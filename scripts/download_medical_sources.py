"""Download official medical reference artifacts into a sibling of the repository."""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = ROOT.parent / "MediKristal-Donnees"
CHUNK_SIZE = 1024 * 1024
MAX_METADATA = 4 * CHUNK_SIZE
INFOWAY = "https://terminologystandardsservice.ca"
CCDD_GUIDE = "https://accelero.infoway-inforoute.ca/en/syndication-feed"
LOINC_API = "https://loinc.regenstrief.org/api/v1/Loinc"
LOINC_VERSION = "2.83"
DPD_BASE = "https://www.canada.ca/content/dam/hc-sc/documents/services/drug-product-database/"
DPD_GUIDE = (
    "https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/"
    "drug-product-database/what-data-extract-drug-product-database.html"
)
HPO_RELEASE = "v2026-09-01"
HPO_BASE = f"https://github.com/obophenotype/human-phenotype-ontology/releases/download/{HPO_RELEASE}/"
ICD_RELEASE = "2026-01"
ICD_BASE = f"https://icdcdn.who.int/static/releasefiles/{ICD_RELEASE}/"
RXNORM_DOC = "https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html"
RXNORM_FULL = "https://download.nlm.nih.gov/umls/kss/rxnorm/RxNorm_full_11022026.zip"
INFOWAY_FEEDS = {
    "ccdd": "external_ccdd",
    "pclocd": "external_pclocd",
    "snomed-ct-ca": "external_snomed",
}


class DownloadError(Exception):
    """An expected failure that can be shown without exposing credentials."""


@dataclass(frozen=True)
class Artifact:
    name: str
    url: str
    reference: str
    version: str = "courante"
    checksum: tuple[str, str] | None = None
    size: int | None = None


PUBLIC = {
    "dpd": tuple(
        Artifact(f"allfiles{suffix}.zip", f"{DPD_BASE}allfiles{suffix}.zip", DPD_GUIDE)
        for suffix in ("", "_ap", "_ia", "_dr")
    ),
    "hpo": tuple(
        Artifact(name, HPO_BASE + name, "https://hpo.jax.org/app/data/annotations", HPO_RELEASE)
        for name in ("hp.obo", "phenotype.hpoa")
    ),
    "cim-11": tuple(
        Artifact(
            f"SimpleTabulation-ICD-11-MMS-{lang}.zip",
            f"{ICD_BASE}SimpleTabulation-ICD-11-MMS-{lang}.zip",
            f"https://icd.who.int/browse/{ICD_RELEASE}/mms/{lang}",
            ICD_RELEASE,
        )
        for lang in ("fr", "en")
    ),
    "orphadata": tuple(
        Artifact(name, f"https://www.orphadata.com/data/xml/{name}", "https://sciences.orphadata.com/phenotypes/")
        for name in ("fr_product4.xml", "en_product4.xml")
    ),
    "rxnorm": (
        Artifact(
            "RxNorm_full_prescribe_11022026.zip",
            "https://download.nlm.nih.gov/rxnorm/RxNorm_full_prescribe_11022026.zip",
            RXNORM_DOC,
            "2026-11-02",
            ("md5", "cd240fc9655dcd2cb54b1e185f3d8702"),
        ),
    ),
}
SOURCES = (*PUBLIC, "loinc", *INFOWAY_FEEDS, "rxnorm-complet")
INFOWAY_FILENAMES = {
    "ccdd": re.compile(r"(?:ccdd_csv_(\d{8})|CanadianClinicalDrugDataSet_(\d{8})_csv)\.zip", re.I),
    "pclocd": re.compile(r"pclocd_(\d{8})\.xlsx", re.I),
    "snomed-ct-ca": re.compile(r"SNOMED_CT_CA_RF2_Release_(\d{8})\.zip", re.I),
}


def https_host(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise DownloadError("URL HTTPS non valide.")
    return parts.hostname


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        original = urlsplit(req.full_url)
        target = urlsplit(newurl)
        https_host(newurl)
        if req.data is not None:
            raise DownloadError("Redirection inattendue pour une demande d’authentification.")
        if original.netloc != target.netloc and "apikey" in {
            key.lower() for key in parse_qs(target.query)
        }:
            raise DownloadError("Redirection refusée pour la clé d’API.")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and original.netloc != target.netloc:
            redirected.remove_header("Authorization")
        return redirected


OPENER = build_opener(HTTPSRedirects())


def request(url: str, *, authorization: str | None = None, data: bytes | None = None):
    https_host(url)
    req = Request(url, data=data, headers={"User-Agent": "MediKristal-MedicalSources/1.0"})
    if authorization:
        req.add_header("Authorization", authorization)
    return OPENER.open(req, timeout=60)


def read_metadata(url: str, **kwargs) -> bytes:
    with request(url, **kwargs) as response:
        payload = response.read(MAX_METADATA + 1)
    if len(payload) > MAX_METADATA:
        raise DownloadError("Métadonnées trop volumineuses.")
    return payload


def credentials(*names: str) -> tuple[str, ...]:
    values = tuple(os.environ.get(name, "") for name in names)
    if not all(values):
        raise DownloadError(f"Accès à configurer dans la session : {', '.join(names)}.")
    return values


def infoway_artifact(source: str, payload: bytes) -> Artifact:
    atom = "{http://www.w3.org/2005/Atom}"
    ncts = "{http://ns.electronichealth.net.au/ncts/syndication/asf/extensions/1.0.0}"
    # Some public feeds declare UTF-8 but contain Windows-1252 text in titles.
    try:
        feed = ET.fromstring(payload)
    except ET.ParseError:
        feed = ET.fromstring(payload.decode("cp1252"))
    candidates = {}
    for entry in feed.findall(f"{atom}entry"):
        for link in entry.findall(f"{atom}link"):
            url = link.get("href", "")
            name = urlsplit(url).path.rsplit("/", 1)[-1]
            release = INFOWAY_FILENAMES[source].fullmatch(name)
            sha256 = link.get(f"{ncts}sha256Hash", "")
            size = link.get("length", "")
            if not release or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
                continue
            if https_host(url) != urlsplit(INFOWAY).netloc:
                continue
            version = next(group for group in release.groups() if group)
            candidates[url] = Artifact(
                name, url, CCDD_GUIDE, version, ("sha256", sha256.lower()),
                int(size) if size.isdecimal() else None,
            )
    if not candidates:
        raise DownloadError("Le flux Inforoute ne propose aucun fichier reconnu avec SHA-256.")
    latest_version = max(artifact.version for artifact in candidates.values())
    latest = [artifact for artifact in candidates.values() if artifact.version == latest_version]
    if len(latest) != 1:
        raise DownloadError("Plusieurs fichiers correspondent à la dernière publication Inforoute.")
    return latest[0]

def resolve_source(source: str) -> tuple[tuple[Artifact, ...], str | None, str | None]:
    if source in PUBLIC:
        return PUBLIC[source], None, None
    if source == "loinc":
        user, password = credentials("MEDIKRISTAL_LOINC_USER", "MEDIKRISTAL_LOINC_PASSWORD")
        authorization = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        artifact = Artifact(
            f"Loinc_{LOINC_VERSION}.zip",
            f"{LOINC_API}/Download?version={LOINC_VERSION}",
            "https://loinc.org/downloads",
            LOINC_VERSION,
            ("md5", "057ddf203164705d5a4c3604257060a4"),
        )
        return (artifact,), authorization, None
    if source in INFOWAY_FEEDS:
        client, secret = credentials("MEDIKRISTAL_INFOWAY_CLIENT_ID", "MEDIKRISTAL_INFOWAY_CLIENT_SECRET")
        feed = f"{INFOWAY}/syndication/alias/{INFOWAY_FEEDS[source]}/syndication.xml"
        artifact = infoway_artifact(source, read_metadata(feed))
        data = urlencode({"grant_type": "client_credentials", "client_id": client, "client_secret": secret}).encode()
        payload = read_metadata(
            f"{INFOWAY}/authorisation/auth/realms/terminology/protocol/openid-connect/token", data=data,
        )
        token = json.loads(payload).get("access_token")
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", token):
            raise DownloadError("Jeton Inforoute absent ou non valide.")
        return (artifact,), f"Bearer {token}", None
    (key,) = credentials("MEDIKRISTAL_UMLS_API_KEY")
    artifact = Artifact(
        "RxNorm_full_11022026.zip", RXNORM_FULL, RXNORM_DOC, "2026-11-02",
        ("md5", "5c57b5f1ff41b268acdec38c412b8a9f"),
    )
    query = urlencode({"url": RXNORM_FULL, "apiKey": key})
    return (artifact,), None, f"https://uts-ws.nlm.nih.gov/download?{query}"


def check_format(path: Path) -> None:
    if path.suffix.lower() in {".zip", ".xlsx"}:
        with zipfile.ZipFile(path) as archive:
            if path.suffix.lower() == ".xlsx" and "xl/workbook.xml" not in archive.namelist():
                raise DownloadError("Le classeur XLSX reçu ne contient pas de workbook.")
            if not any(info.file_size for info in archive.infolist() if not info.is_dir()):
                raise DownloadError("L’archive ZIP ne contient aucune donnée.")
        return
    with path.open("rb") as stream:
        first = stream.read(CHUNK_SIZE).decode("utf-8-sig", errors="replace").lstrip()
    signatures = {".xml": ("<?xml", "<JDBOR"), ".obo": ("format-version:",), ".hpoa": ("#", "database_id")}
    if not first.startswith(signatures[path.suffix]):
        raise DownloadError("Le fichier reçu ne correspond pas au format attendu.")


def download(root: Path, source: str, artifact: Artifact, authorization=None, request_url=None) -> Path:
    source_dir = root / source
    source_dir.mkdir(parents=True, exist_ok=True)
    published_algorithm, published_digest = artifact.checksum or (None, None)
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False) if published_algorithm == "md5" else None
    received = 0
    with tempfile.TemporaryDirectory(prefix=".telechargement-", dir=source_dir) as temp:
        bundle = Path(temp) / "bundle"
        bundle.mkdir()
        path = bundle / artifact.name
        try:
            with request(request_url or artifact.url, authorization=authorization) as response, path.open("wb") as output:
                length = response.headers.get("Content-Length", "")
                last_modified = response.headers.get("Last-Modified")
                while chunk := response.read(CHUNK_SIZE):
                    output.write(chunk)
                    received += len(chunk)
                    sha256.update(chunk)
                    if md5:
                        md5.update(chunk)
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            curl = shutil.which("curl.exe") or shutil.which("curl")
            if (not curl or source != "dpd" or authorization or request_url or
                    artifact.url != DPD_BASE + artifact.name):
                raise
            print("  Nouvelle tentative BDPP avec curl.")
            subprocess.run(
                [curl, "--disable", "--fail", "--silent", "--location", "--proto", "=https",
                 "--proto-redir", "=https", "--connect-timeout", "15", "--max-time", "180",
                 "--output", str(path), artifact.url],
                check=True, timeout=190,
            )
            length, last_modified = "", None
            received = path.stat().st_size
            with path.open("rb") as stream:
                sha256 = hashlib.file_digest(stream, "sha256")
                if md5:
                    stream.seek(0)
                    md5 = hashlib.file_digest(stream, lambda: hashlib.md5(usedforsecurity=False))
        if not received or (length.isdecimal() and int(length) != received):
            raise DownloadError("Fichier vide ou téléchargement incomplet.")
        if artifact.size is not None and received != artifact.size:
            raise DownloadError("Taille différente de celle publiée.")
        digest = sha256.hexdigest()
        computed = md5.hexdigest() if md5 else digest
        if published_digest and published_digest != computed:
            raise DownloadError("Empreinte différente de celle publiée.")
        check_format(path)
        metadata = {
            "source": source,
            "source_reference": artifact.reference,
            "artifact_url": artifact.url.split("?")[0] if source in INFOWAY_FEEDS else artifact.url,
            "filename": artifact.name,
            "version": artifact.version,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "http_last_modified": last_modified,
            "bytes": received,
            "sha256": digest,
            "publisher_checksum": dict([artifact.checksum]) if artifact.checksum else None,
            "status": "downloaded",
        }
        (bundle / "provenance.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        target = source_dir / artifact.name / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            bundle.rename(target)
        except OSError:
            existing = target / artifact.name
            with existing.open("rb") as stream:
                existing_digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if existing_digest != digest or not (target / "provenance.json").is_file():
                raise DownloadError(f"Copie existante incomplète ou endommagée : {target}") from None
    return target / artifact.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", metavar="SOURCE", help="Sources à télécharger. Sans argument : lot public.")
    parser.add_argument("--all", action="store_true", help="Inclure les sources à accès contrôlé.")
    parser.add_argument("--list", action="store_true", help="Afficher les sources et la destination sans connexion.")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DESTINATION, help="Dossier de destination, hors du dépôt.")
    args = parser.parse_args(argv)
    root = args.dest.resolve()
    if root == ROOT or ROOT in root.parents:
        parser.error("La destination doit être hors du dépôt MediKristal.")
    if args.list:
        print(f"Destination : {root}")
        print(f"Lot public : {', '.join(PUBLIC)}")
        print(f"Accès contrôlé : {', '.join(SOURCES[len(PUBLIC):])}")
        return 0
    if args.all and args.sources:
        parser.error("--all ne se combine pas avec une liste de sources.")
    sources = SOURCES if args.all else tuple(dict.fromkeys(args.sources)) or tuple(PUBLIC)
    unknown = set(sources) - set(SOURCES)
    if unknown:
        parser.error(f"Sources inconnues : {', '.join(sorted(unknown))}. Voir --list.")
    failed = False
    print(f"Destination : {root}")
    for source in sources:
        try:
            artifacts, authorization, request_url = resolve_source(source)
        except (DownloadError, OSError, ValueError, ET.ParseError, AttributeError, http.client.HTTPException) as error:
            report_error(source, error)
            failed = True
            continue
        for artifact in artifacts:
            try:
                print(f"{source} / {artifact.name}…", flush=True)
                path = download(root, source, artifact, authorization, request_url)
                print(f"  OK {path}")
            except (DownloadError, OSError, ValueError, zipfile.BadZipFile, http.client.HTTPException, subprocess.SubprocessError) as error:
                report_error(source, error)
                failed = True
    return int(failed)


def report_error(source: str, error: Exception) -> None:
    if isinstance(error, DownloadError):
        message = str(error)
    elif isinstance(error, HTTPError):
        message = f"Erreur HTTP {error.code}. Vérifier l’accès auprès du fournisseur."
    elif isinstance(error, (URLError, TimeoutError, http.client.HTTPException)):
        message = "Connexion interrompue ou indisponible. Relancer la source."
    else:
        message = f"Le fournisseur ou le dossier local n’a pas pu être traité ({type(error).__name__})."
    print(f"{source} : {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

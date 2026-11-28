"""Build and query a local MediKristal reference index from verified downloads."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import tempfile
import unicodedata
import zipfile
from contextlib import closing
from itertools import chain
from pathlib import Path
from xml.etree import ElementTree as ET


REPO = Path(__file__).resolve().parents[1]
DATA = REPO.parent / "MediKristal-Donnees"
DPD = ("", "_ap", "_ia", "_dr")
ICD = "SimpleTabulation-ICD-11-MMS-"
RXNORM = "RxNorm_full_prescribe_11022026.zip"
EXPECTED = {
    "dpd": tuple(f"allfiles{suffix}.zip" for suffix in DPD),
    "hpo": ("hp.obo", "phenotype.hpoa"),
    "cim-11": tuple(f"{ICD}{language}.zip" for language in ("fr", "en")),
    "orphadata": tuple(f"{language}_product4.xml" for language in ("fr", "en")),
    "rxnorm": (RXNORM,),
}
PROFILE = "medikristal-public-reference/1"
MAX_FILE = 512 * 1024**2
RRF = {
    "RXNCONSO": "RXCUI LAT TS LUI STT SUI ISPREF RXAUI SAUI SCUI SDUI SAB TTY CODE STR SRL SUPPRESS CVF",
    "RXNREL": "RXCUI1 RXAUI1 STYPE1 REL RXCUI2 RXAUI2 STYPE2 RELA RUI SRUI SAB SL RG DIR SUPPRESS CVF",
    "RXNSAT": "RXCUI LUI SUI RXAUI STYPE CODE ATUI SATUI ATN SAB ATV SUPPRESS CVF",
}
DRUG = "drug_code product_categorization class din brand_name descriptor pediatric_flag accession_number number_of_ais last_update_date ai_group_no class_fr brand_name_fr descriptor_fr"
INGREDIENT = "drug_code active_ingredient_code ingredient ingredient_supplied_ind strength strength_unit strength_type dosage_value base dosage_unit notes ingredient_fr strength_unit_fr strength_type_fr dosage_unit_fr"
STATUS = "drug_code current_status_flag status history_date status_fr lot_number expiration_date"

SCHEMA = """
CREATE TABLE source_file (
    id INTEGER PRIMARY KEY, source TEXT NOT NULL, filename TEXT NOT NULL,
    sha256 TEXT NOT NULL, provenance TEXT NOT NULL, UNIQUE(source, filename)
);
CREATE TABLE record (
    id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES source_file(id),
    kind TEXT NOT NULL, code TEXT NOT NULL, label TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX record_by_code ON record(code COLLATE NOCASE);
CREATE VIRTUAL TABLE lookup USING fts5(label, tokenize='unicode61 remove_diacritics 2');
"""


def verified_files(root: Path):
    for source, names in EXPECTED.items():
        for name in names:
            home = root / source / name
            candidates = sorted(
                path for path in home.glob("*/provenance.json")
                if re.fullmatch("[0-9a-f]{64}", path.parent.name)
            )
            if len(candidates) != 1:
                raise ValueError(f"{source}/{name} : attendu une copie avec provenance, trouvé {len(candidates)}.")
            receipt = candidates[0]
            metadata = json.loads(receipt.read_text(encoding="utf-8-sig"))
            path = receipt.with_name(name)
            size = path.stat().st_size
            if not 0 < size <= MAX_FILE:
                raise ValueError(f"Taille non admise : {path}")
            if (metadata["source"], metadata["filename"], metadata["sha256"], metadata["bytes"]) != (
                source, name, receipt.parent.name, size
            ):
                raise ValueError(f"Provenance incohérente : {receipt}")
            with path.open("rb") as stream:
                sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
            if sha256 != metadata["sha256"]:
                raise ValueError(f"SHA-256 différent du reçu : {path}")
            yield source, path, metadata


def titled_rows(rows, required):
    header = next(rows)
    if len(set(header)) != len(header) or not set(required) <= set(header):
        raise ValueError(f"En-têtes incompatibles avec {required}")
    yield from fixed_rows(rows, header)


def fixed_rows(rows, fields, *, trailing=False):
    for row in rows:
        if not row:
            continue
        if trailing:
            if row[-1] != "":
                raise ValueError("Séparateur terminal RRF absent.")
            row = row[:-1]
        if len(row) != len(fields):
            raise ValueError(f"Nombre de champs attendu : {len(fields)}, lu : {len(row)}")
        yield dict(zip(fields, row))


def archive_rows(path: Path, member: str, delimiter: str):
    with zipfile.ZipFile(path) as archive:
        matches = [entry for entry in archive.infolist() if entry.filename == member]
        if len(matches) != 1 or not 0 < matches[0].file_size <= MAX_FILE:
            raise ValueError(f"Membre ZIP absent, ambigu ou trop volumineux : {member}")
        with archive.open(matches[0]) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
            yield from csv.reader(text, delimiter=delimiter, quoting=csv.QUOTE_NONE if delimiter == "|" else csv.QUOTE_MINIMAL, strict=True)


def dpd_records(path):
    suffix = path.stem.removeprefix("allfiles")
    for raw in fixed_rows(archive_rows(path, f"drug{suffix}.txt", ","), DRUG.split()):
        yield "dpd-produit", raw["din"], raw["brand_name"], raw
    for raw in fixed_rows(archive_rows(path, f"ingred{suffix}.txt", ","), INGREDIENT.split()):
        yield "dpd-ingredient", raw["drug_code"], raw["ingredient"], raw
    for raw in fixed_rows(archive_rows(path, f"status{suffix}.txt", ","), STATUS.split()):
        yield "dpd-statut", raw["drug_code"], "", raw


def hpo_terms(path):
    fields = None
    with path.open(encoding="utf-8-sig") as stream:
        for line in chain(stream, ("[End]",)):
            line = line.rstrip()
            if line.startswith("["):
                if fields is not None:
                    yield "hpo-terme", fields["id"][0], fields["name"][0], fields
                fields = {} if line == "[Term]" else None
            elif fields is not None and line and not line.startswith("!"):
                key, separator, value = line.partition(": ")
                if not separator:
                    raise ValueError("Champ OBO non valide.")
                fields.setdefault(key, []).append(value)


def hpo_annotations(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader((line for line in stream if not line.startswith("#")), delimiter="\t", strict=True)
        for raw in titled_rows(rows, ("database_id", "disease_name", "hpo_id", "qualifier", "reference")):
            yield "hpo-annotation", raw["database_id"], raw["disease_name"], raw


def checked_member(archive, name):
    matches = [entry for entry in archive.infolist() if entry.filename == name]
    if len(matches) != 1 or not 0 < matches[0].file_size <= MAX_FILE:
        raise ValueError(f"Membre d’archive absent, ambigu ou trop volumineux : {name}")
    return matches[0]


def xml_without_entities(stream):
    overlap = b""
    while chunk := stream.read(1024 * 1024):
        data = overlap + chunk
        if b"\0" in data or b"<!DOCTYPE" in data or b"<!ENTITY" in data:
            raise ValueError("Déclaration XML non admise.")
        overlap = data[-9:]
    stream.seek(0)
    return stream


def workbook_rows(archive):
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with archive.open(checked_member(archive, "xl/sharedStrings.xml")) as stream:
        entries = ET.parse(xml_without_entities(stream)).getroot()
        strings = ["".join(node.text or "" for node in item.iter(ns + "t")) for item in entries]
    with archive.open(checked_member(archive, "xl/worksheets/sheet1.xml")) as stream:
        for _, item in ET.iterparse(xml_without_entities(stream), events=("end",)):
            if item.tag != ns + "row":
                continue
            result = {}
            for cell in item.findall(ns + "c"):
                column = re.sub(r"\d+$", "", cell.attrib["r"])
                value = cell.findtext(ns + "v", "")
                result[column] = strings[int(value)] if cell.get("t") == "s" else value
            yield result
            item.clear()


def icd_records(path):
    # Use the publisher's workbook because the TSV contains unquoted multiline notes.
    with zipfile.ZipFile(path) as archive:
        name = f"{path.stem}.xlsx"
        with zipfile.ZipFile(io.BytesIO(archive.read(checked_member(archive, name)))) as workbook:
            rows = workbook_rows(workbook)
            header = {column: label for column, label in next(rows).items() if label}
            if not {"Foundation URI", "Linearization URI", "Code", "Title"} <= set(header.values()):
                raise ValueError("En-tête CIM-11 invalide.")
            for row in rows:
                raw = {field: row.get(column, "") for column, field in header.items()}
                code = raw["Code"] or raw["Linearization URI"] or raw["Foundation URI"]
                if code:
                    yield "cim-11", code, raw["Title"], raw
                elif any(raw.values()):
                    raise ValueError("Ligne CIM-11 sans identifiant.")


def orpha_records(path):
    with path.open("rb") as stream:
        events = ET.iterparse(xml_without_entities(stream), events=("start", "end"))
        _, root = next(events)
        if root.tag != "JDBOR":
            raise ValueError("Racine Orphadata inconnue.")
        for event, element in events:
            if event != "end" or element.tag != "HPODisorderSetStatus":
                continue
            disorder = element.find("Disorder")
            if disorder is None:
                raise ValueError("Fiche Orphadata sans maladie.")
            yield "orphadata-maladie", disorder.findtext("OrphaCode"), disorder.findtext("Name"), {
                "xml": ET.tostring(disorder, encoding="unicode"),
                "release_date": root.get("date"),
            }
            element.clear()


def rxnorm_records(path):
    for table, fields in RRF.items():
        rows = archive_rows(path, f"rrf/{table}.RRF", "|")
        for raw in fixed_rows(rows, fields.split(), trailing=True):
            code = raw.get("RXCUI") or raw.get("RXCUI1") or raw.get("RXCUI2") or raw.get("RUI")
            yield table.lower(), code, raw.get("STR", ""), raw


def records(source, path):
    if source == "dpd":
        return dpd_records(path)
    if source == "hpo":
        return hpo_terms(path) if path.name == "hp.obo" else hpo_annotations(path)
    if source == "cim-11":
        return icd_records(path)
    if source == "orphadata":
        return orpha_records(path)
    return rxnorm_records(path)


def insert_records(db, file_id, source, path):
    batch = []
    count = 0
    for kind, code, label, raw in records(source, path):
        # Some relationship rows identify atoms, rather than concepts.
        if source == "rxnorm" and not code:
            code = raw.get("RXAUI") or raw.get("RXAUI1") or raw.get("RXAUI2")
        if not code or label is None:
            raise ValueError(f"Identité ou libellé absent dans {path.name}, ligne logique {count + 1}")
        batch.append((file_id, kind, code, label, json.dumps(raw, ensure_ascii=False)))
        count += 1
        if len(batch) >= 2000:
            db.executemany("INSERT INTO record(file_id, kind, code, label, data) VALUES (?,?,?,?,?)", batch)
            batch.clear()
    if not count:
        raise ValueError(f"Aucun enregistrement reconnu : {path.name}")
    db.executemany("INSERT INTO record(file_id, kind, code, label, data) VALUES (?,?,?,?,?)", batch)
    return count


def build(root: Path):
    files = list(verified_files(root))
    identity = json.dumps([PROFILE, [(source, path.name, item["sha256"]) for source, path, item in files]])
    digest = hashlib.sha256(identity.encode()).hexdigest()
    output = root / "index-public"
    output.mkdir(exist_ok=True)
    target = output / f"{digest}.sqlite3"
    if target.is_file():
        return target
    with tempfile.TemporaryDirectory(prefix=".import-", dir=output) as stage:
        temp = Path(stage) / target.name
        with closing(sqlite3.connect(temp)) as db, db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA)
            for source, path, item in files:
                cursor = db.execute(
                    "INSERT INTO source_file(source,filename,sha256,provenance) VALUES (?,?,?,?)",
                    (source, path.name, item["sha256"], json.dumps(item, ensure_ascii=False)),
                )
                count = insert_records(db, cursor.lastrowid, source, path)
                print(f"{source} / {path.name} : {count:,}", flush=True)
            db.execute("INSERT INTO lookup(rowid, label) SELECT id, label FROM record WHERE label <> ''")
            db.execute("PRAGMA user_version=1")
        os.replace(temp, target)
    return target


def search(path: Path, query: str, limit: int):
    # Construct a literal FTS conjunction and keep native-code lookup separate.
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFC", query))
    expression = " AND ".join(f'"{word}"' for word in words)
    sql = """
        SELECT s.source, r.kind, r.code, r.label, s.filename, s.sha256
        FROM record r JOIN source_file s ON s.id=r.file_id
        WHERE r.code=? COLLATE NOCASE OR r.id IN (SELECT rowid FROM lookup WHERE lookup MATCH ?)
        ORDER BY r.code<>? COLLATE NOCASE, r.id LIMIT ?
    """
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute(sql, (query, expression or '""', query, limit)).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA, help="Dossier des téléchargements.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="Vérifier les 11 fichiers et produire l’index.")
    lookup = commands.add_parser("search", help="Chercher dans un index déjà construit.")
    lookup.add_argument("index", type=Path)
    lookup.add_argument("query")
    lookup.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    try:
        if args.command == "build":
            root = args.data.resolve()
            if root == REPO or REPO in root.parents:
                raise ValueError("Le dossier des données doit être hors du dépôt.")
            print(f"Index : {build(root)}")
        else:
            if not 1 <= args.limit <= 100:
                raise ValueError("La limite doit être de 1 à 100.")
            for match in search(args.index, args.query, args.limit):
                print(json.dumps(match, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, StopIteration, csv.Error, sqlite3.Error, zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(1, f"Import ou recherche interrompu : {error}\n")


if __name__ == "__main__":
    main()

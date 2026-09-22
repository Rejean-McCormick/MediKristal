# 15 — Interfaces et parcours

## Application patient

Saisie progressive avec langage accessible, option « je ne sais pas », contexte temporel, vérification des unités et possibilité de corriger. Import de document explicite ; extraction proposée à confirmer lorsque nécessaire. Montrer limites de couverture, fraîcheur et informations manquantes dans le contexte de l'action. Une hypothèse est nommée hypothèse ; pas de confirmation implicite par une couleur verte.

L'utilisateur peut comprendre pourquoi une question ou un examen est proposé. Éviter les chiffres de précision excessive ; afficher un intervalle lorsque disponible, sans le fabriquer. Les alternatives incluent consultation/orientation selon protocole. Une absence de score ne signifie pas absence de risque. Les commandes réservées à des professionnels restent protégées au serveur, pas seulement masquées.

## Console professionnelle

Vue chronologique du cas, identité vérifiée, observations actives/corrigées, modèle et protocole utilisés, hypothèses avec type de résultat, éléments pour/contre, manquants et conflits. Actions accepter/refuser/modifier avec raison ; afficher les conséquences d'une modification du cas sur les propositions existantes. Accès à la provenance sans obliger à lire une trace technique brute pour chaque décision.

Comparateur : bénéfices attendus documentés, incertitude, délai, disponibilité, coûts selon perspective et contraintes. Afficher lorsque le meilleur parcours théorique n'est pas disponible, plutôt que le supprimer de l'explication. Une demande en cours et une réservation confirmée ont un affichage distinct.

## Administration

Catalogues, sites, ressources, personnel, maintenance, devis et imports. Séparer permissions de configuration technique, gestion des coûts et approbation de politiques cliniques. Tableau des données périmées, slots incertains, connecteurs en panne, jobs et réconciliations. Les secrets sont écrits/remplacés, jamais révélés en clair.

## Atelier scientifique

Recherche des artefacts, diff, dépôt de preuve, description de population, comparaison versions et rapports d'évaluation. Les auteurs voient l'état de leur proposition. Les réviseurs disposent des conflits d'intérêt et du graphe d'impact. L'accès aux cas individuels n'est pas accordé par le seul rôle chercheur.

## Internationalisation et accessibilité

Français initial avec anglais prévu ; clés de traduction séparées des codes. Conserver langue source, traduction et validation lorsque le sens clinique peut changer. Dates/devises/unités localisées sans modifier la donnée canonique. Navigation clavier, contrastes, lecteurs d'écran, texte redimensionnable et alternatives aux graphiques sont des critères d'acceptation. Le produit hors ligne doit afficher les mêmes états d'erreur que le web.

## Alerte et fatigue

Classer notifications par impact et propriétaire, dédupliquer répétitions, permettre acquittement sans effacer la cause. Un acquittement n'est pas résolution. Les seuils d'escalade sont ceux des protocoles/politiques admis. Mesurer bruit et refus, sans diminuer automatiquement un garde clinique pour améliorer un taux d'acceptation.

## Navigation proposée

Accueil/capacités ; cas/chronologie ; hypothèses ; prochaines actions ; résultats ; traitements/suivi ; connaissances ; contributions ; ressources ; administration. Les vues communes partagent API et composants d'explication, mais droits et vocabulaire sont adaptés au contexte. Pas de terminologie interne Kristal, engine hash ou solver gap dans le flux patient principal ; détails techniques consultables par rôles appropriés.

# Corpus d'exemples synthétiques

Toutes les données, identités, prix, sites, maladies et tests de ce dossier sont fictifs. Ils n'expriment aucune estimation clinique. Les digests composés de `a` sont des placeholders syntaxiques, **pas des empreintes vérifiées d'artefacts**. Ils doivent être refusés pour une admission réelle sans objets correspondants vérifiés.

`index.json` associe chaque exemple à sa définition dans `contracts/domain.schema.json`. Les exemples couvrent des objets isolés ; ils ne constituent pas une base applicative entièrement peuplée (notamment ordre et sujet référencés). Le validateur vérifie leur forme, non une intégrité référentielle globale inexistante.

L'oracle probabiliste binaire emploie prévalence 0,10, sensibilité 0,80 et spécificité 0,90, exclusivement à des fins arithmétiques. Il est incompatible avec un usage clinique. L'absence d'intervalle et de calibration dans cet exemple est explicite.

Les cas négatifs sont construits par le validateur : propriété inattendue, probabilité hors bornes, score présenté comme probabilité et observation inconnue avec valeur. Les contrôles d'identité, temporalité, unités et permissions exigent les tests applicatifs décrits dans les chapitres.

# Tomate Flutter (offline-first)

Cette application Flutter embarque toute la logique metier du backend FastAPI. Aucun serveur n'est necessaire : tout fonctionne en local avec SQLite.

## Architecture

La structure suit une Clean Architecture simplifiee :

- `lib/domain` : entites et regles metier pures.
- `lib/application` : moteur `PomodoroEngine` et use-cases.
- `lib/data` : persistance locale SQLite (via Drift) et repositories.
- `lib/services` : temps, notifications locales, planification.
- `lib/presentation` : UI Flutter et state management Riverpod.

Le moteur `PomodoroEngine` est la source de verite : la UI ne calcule jamais l'etat metier, elle interroge uniquement le moteur.

## Modele temporel robuste

- Tous les etats critiques sont derives de timestamps stockes en base (`start_at`, `end_at`, `planned_minutes`).
- L'etat est recalcule a chaque ouverture, action utilisateur et tick UI.
- Aucun timer en memoire ne detient de verite metier.

## Persistance

La base SQLite est creee localement dans le dossier applicatif (`tomato.db`). Les tables correspondent au backend :

- `settings`
- `daily_state`
- `tasks`
- `sessions`
- `pause_cards`
- `pause_card_uses`

## Lancer l'app

Depuis le dossier `flutter/` :

```bash
flutter pub get
flutter run
```

Si Gradle signale un wrapper manquant, regenez-le une fois depuis `flutter/android/` :

```bash
gradle wrapper
```

Pour iOS, vous pouvez ajouter la plateforme via :

```bash
flutter create --platforms=ios .
```

## Choix techniques

- Flutter stable
- Riverpod pour l'etat
- Drift pour SQLite (requete SQL manuelle, sans generation)
- `flutter_local_notifications` pour les alertes de fin de session

## Fonctionnalites principales

- Sessions focus / pause avec persistance
- Planification de sessions
- Cartes pause avec quotas
- Taches et historique
- Reglages de base (durees, notifications)

## Notes

- Les notifications sont declenchees sur la fin de session planifiee.
- Les changements d'heure et redemarrages sont absorbes via recalcul.

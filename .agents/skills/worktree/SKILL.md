---
name: worktree
description: Crée un worktree isolé, implémente un ticket, lance les tests, commit et push avec création de MR/PR. Use when asked to implement a feature in a worktree or when told to start a worktree for a ticket.
user-invocable: true
---

Implémente un ticket dans un worktree isolé, du début jusqu'à la MR/PR.

**Signature :** `/worktree <TICKET_ID> <description courte de la feature> [@chemin/vers/ticket.md | détail inline]`

Si le numéro de ticket ou le détail d'implémentation manque, demande-les avant de continuer.

---

## Étape 1 — Extraire les informations

Depuis les args :
- **`TICKET_ID`** : identifiant du ticket tel que fourni (ex. `ATL-42`, `JIRA-123`, `GH-7`)
- **`FEATURE_SLUG`** : slug kebab-case dérivé de la description courte (ex. `backend-create-perimeter`)
- **Détail d'implémentation** : contenu du fichier `@...` ou texte inline

Le nom de branche à créer : `<TICKET_ID>/<feature_slug>`
Exemple : `ATL-42/backend-create-perimeter`

Vérifie dans le CLAUDE.md du projet si une convention de nommage de branche est définie et applique-la en priorité.

---

## Étape 2 — Créer le worktree

Utilise l'outil `EnterWorktree` avec `name: "<TICKET_ID>-<feature_slug>"`.

Le worktree sera créé sous `.claude/worktrees/` sur une branche fraîche depuis la branche par défaut du projet (généralement `origin/main` ou `origin/develop` — vérifie via `git symbolic-ref refs/remotes/origin/HEAD`).

Une fois dans le worktree, vérifie que tu es bien sur la bonne branche :

```bash
git branch --show-current
```

Renomme la branche pour respecter la convention `<TICKET_ID>/<feature_slug>` (ou la convention du projet) :

```bash
git branch -m <TICKET_ID>/<feature_slug>
```

---

## Étape 3 — Lire le ticket et comprendre la portée

Lis le fichier de ticket s'il est référencé (`@chemin`), ou utilise le détail inline.

Identifie :
- Les fichiers à créer ou modifier
- Les skills ou règles applicables au projet (consulte le CLAUDE.md du projet pour les références)

Lis `.claude/rules/architecture.md` et charge le skill `ub-mode` s'il est installé. Écris ensuite ton plan d'architecture : types du domaine, fonctions pures, ports, adaptateurs, point d'entrée qui les assemble. Il va dans ton rapport final, sous forme de tableau couche / module / rôle, et pas dans la PR.

---

## Étape 4 — Implémenter

Utilise `TodoWrite` pour tracker les tâches issues du ticket.

Respecte les contraintes du ticket à la lettre : ne pas ajouter de fonctionnalités hors scope, ne pas refactorer ce qui n'est pas demandé.

---

## Étape 5 — Vérifier

Consulte le CLAUDE.md du projet pour connaître les commandes de lint et de test à exécuter. En l'absence d'instructions, inspecte le `Makefile`, `package.json`, ou les scripts disponibles à la racine.

Lance lint puis tests dans l'ordre indiqué. Si une étape échoue, corrige avant de passer à la suivante. Ne déclare pas l'implémentation terminée tant que tout n'est pas vert.

Lance `make check` (format, lint, types, code mort, tests avec couverture), puis les gates `ub-mode` s'ils sont installés, et corrige ou justifie chaque échec :

```bash
make check
uv run --script ~/.claude/skills/ub-mode/scripts/quality.py --base origin/dev --tests tests
```

Fais ensuite la vérification d'avant push de `.claude/rules/architecture.md` (§ Design before code) sur les modules ajoutés ou modifiés :

- les imports de chaque module, et leur sens : le domaine vers les ports, les adaptateurs et les utils ; un adaptateur vers les ports, les constantes et les utils seulement, imports sous `TYPE_CHECKING` compris ;
- les formats fournisseurs dans le domaine : `subprocess`, URL, refs git, Markdown, `<!--`, options de ligne de commande, `owner/name` ;
- les fonctions ajoutées avec plus de deux paramètres positionnels ;
- un test de relance et un test de reprise après un échec à mi-chemin pour chaque étape qu'une relance peut répéter.

Corrige chaque écart avant le commit, et note le résultat dans ton rapport final, avec celui des gates.

---

## Étape 6 — Commit

Stage uniquement les fichiers produits par cette implémentation (pas `.claude/settings.json` ni fichiers temporaires) :

```bash
git add <fichiers explicitement modifiés ou créés>
```

Commit en respectant les [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <description impérative en anglais>

[corps optionnel si nécessaire]
```

Types courants : `feat`, `fix`, `refactor`, `test`, `chore`.
Scope : module ou couche concernée.
La description doit tenir sur une ligne, en anglais, à l'impératif.

---

## Étape 7 — Push

```bash
git push -u origin <TICKET_ID>/<feature_slug>
```

---

## Étape 8 — Créer la MR/PR

Détermine la forge à partir de l'URL du remote :

```bash
git remote get-url origin
```

**Si GitHub** (`github.com`) — utilise le CLI `gh` :

```bash
gh pr create \
  --title "<conventional_commit> (<TICKET_ID>)" \
  --body "..." \
  --base <default-branch>
```

**Si GitLab** (autre) — utilise le CLI `glab` si disponible :

```bash
glab mr create \
  --title "<conventional_commit> (<TICKET_ID>)" \
  --description "..." \
  --target-branch <default-branch> \
  --remove-source-branch
```

Si `glab` n'est pas disponible, utilise l'API GitLab via `curl`. Récupère le token via `git credential fill` sur l'hôte du remote. Si le token est vide, arrête et demande à l'utilisateur de configurer `git credential`.

**Format de la description MR/PR (court et direct) :**

```
## Intention

<1-2 phrases expliquant ce que fait ce ticket et pourquoi.>

## Points d'attention

- <point d'attention 1 si pertinent>
- <point d'attention 2 si pertinent>

_(Omettre cette section s'il n'y a rien de notable.)_
```

Pas de liste exhaustive des fichiers modifiés, pas de reproduction du HOW du ticket. L'intention et les éventuels risques suffisent.

Affiche l'URL de la MR/PR créée à la fin.

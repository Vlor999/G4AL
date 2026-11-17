---
name: writing
description: |
  Edit prose written for a human reader so it reads like a person wrote it:
  specs, designs, PVs, plans, PR descriptions, wiki pages, messages, slides, and
  comments in code, workflows and configuration files.
  Use when writing or reviewing such text, or when another skill asks for a writing
  pass. Applies humanizer, the French forms when the text is in French, and
  this repo's own rules.
---

# Writing

Run these steps in order on the text.

1. Read [humanizer.md](humanizer.md) and apply it. When another task calls this
   skill (a spec, a PR description, a wiki page), use its embedded mode and
   return only the final text.
2. When the text is in French, also read [french.md](french.md).
3. Apply the repo rules below.
4. On slides, keep only the rules listed under « Slides ».

When rules conflict, a document's template (`SPEC.md`, `DESIGN.md`, `PV.md`,
an OpenWiki page type) decides the format, and the repo rules below win over
humanizer.

## Repo rules

### Tie each sentence to the one before

A person who argues ties their sentences together; a model sets them side by
side. Say how a sentence follows from the previous one, with a linking word
that names the relation: cause (parce que, puisque, car), consequence (donc,
alors, si bien que, ce qui), concession (pourtant, alors que, même si, en
revanche), condition or time (si, tant que, dès que, quand). Aim for at least
one sentence in two tied to the one before. The linking word must carry real
reasoning: « X, donc Y » holds only if Y follows from X.

### Never fix a tell by splitting it

Cutting a tell into two short sentences, or swapping its halves, leaves it
recognizable. Rewrite it as one sentence that states the relation.

- Tell: « Ce n'est pas un problème de recrutement, c'est un problème de
  process. »
- Still recognizable: « Le problème vient du process. Le recrutement n'y est
  pour rien. »
- Fixed: « Le problème vient du process, ce qui explique pourquoi recruter
  davantage n'y changerait rien. »

### No question answered at once

A question asked only to answer it in the next words (« Le résultat ? »,
« La clé ? », « Pourquoi ? Parce que… ») stages the point. State it. The same
goes for a countdown that rejects two or three options before revealing the
right one.

### Concise, never at the cost of stacked implicit

Aim for short sentences, but not by dropping what a reader outside the
conversation needs to follow them. A shorthand coined while working (« la
liste de PH »), a subject that is not the real actor, or a qualifier that
stands for a whole step each leave one thing implicit; two or three in one
sentence make it unreadable.

The author cannot see their own implicit, since they reread with the whole
conversation in mind. On a spec, a design, a PV or a plan, hand the file to
a fresh agent that sees nothing else, and ask it to list each sentence it
cannot follow without guessing, with the exact question it asks itself
(« what is the cast? », « who freezes what? »), and no rewrite. Then answer
the questions in the text yourself, since only you know the answer.

Sort the questions before answering. A strict fresh reader always finds
something, and answering every nitpick makes the text grow again: answer
what makes a reader misunderstand or guess, and a detail only when a short
rewording settles it. Three rounds are usually enough; past them the gain
per round drops to almost nothing.

Answer by adding short sentences, never by packing the answer into the old
one. Stuffing it in as an aside, a parenthesis or a relative clause trades
the implicit for a sentence nobody can follow either.

- One answer, one short sentence. Split rather than chain.
- Define a coined term once, where it first appears, then use it as is.
- Say what happens concretely, in the reader's words, not the code's: what
  the code name does matters more than the name itself.
- Cut what the reader does not need to follow the point (history, internal
  plumbing), instead of explaining it. Never cut a fact the reader needs to
  build or decide (a matching rule, a filter, a limit) to save words: cut
  repetitions instead.
- A list of more than three explained items becomes a sub-list, one item
  per line.

Example, from a design:

- Implicit: « Un tour que le produit perd devient une passe non jouée. »
- Packed: « Un tour que le chief of staff n'achève pas (`TurnFailed`, ou un
  tour interrompu, par exemple à la limite de récursion du graphe) devient
  une passe non jouée, avec sa raison. »
- Fixed: « Si le chief of staff plante ou s'arrête avant d'avoir répondu
  (erreur, limite d'étapes atteinte), la passe compte comme non jouée. »

## Slides

A slide is titles and short bullets, so the rules about sentences and
paragraphs give way to its format. Apply only these:

- humanizer §1, §3, §4, §5, §8, §9, §12 to §18, §20 to §23, and in §2 the
  self-applauding closers (« Et ça change tout », « Tout est dit »);
- every French form in `french.md` for those patterns, and all its French
  tells (« tenir » included);
- « No question answered at once » and « Concise, never at the cost of
  stacked implicit » above.

Fragments, bullets with labels, triads of bullets, repeated openings and
untied sentences are allowed on a slide. Speaker notes are prose and follow
every rule.

# Simulateur de capteur PMU

Implémentation Python modulaire d'un PMU triphasé : génération des signaux, bruit,
phaseurs LS, composantes symétriques, fréquence/ROCOF, transmission et rendu sont
séparés. Le moteur ne dépend pas de Matplotlib ; l'animation relit uniquement le
fichier NPZ sauvegardé.

## Installation et commandes exactes

```bash
python -m pip install -e '.[test]'
pmu-sim simulate examples/nominal.json -o nominal.npz
pmu-sim animate nominal.npz -o nominal.gif --fps 20 --mode continuous \
  --parameter "fréquence = 50 Hz"
# MP4 demande ffmpeg :
pmu-sim animate nominal.npz -o nominal.mp4 --fps 25
pytest -q
```

`examples/frequency_ramp.json` illustre rampe, bruit et rapport de cadence non
entier. Les profils acceptés sont `constant`, `step`, `ramp` et `sine`. Les angles
de configuration sont en degrés et sont immédiatement convertis en radians. Le
champ `noise_variances` accepte une variance commune ou trois variances ; le
générateur emploie bien leur racine carrée.

## Architecture et conventions

* `config.py` décrit/valide les profils et les fenêtres ;
* `signals.py` et `noise.py` construisent les données et vérités théoriques ;
* `phasor.py`, `frequency.py` et `symmetrical.py` sont des estimateurs isolés ;
* `operators.py` met en cache `S`, `K`, `B`, `G` et la transformation symétrique ;
* `transmission.py` planifie exactement `m/f_r` et choisit la dernière mesure
  disponible (temps de disponibilité distinct du temps représentatif) ;
* `results.py` sauvegarde toutes les séries, validités et métadonnées dans NPZ ;
* `animation.py` reconstruit le rendu depuis ce NPZ, avec une cadence visuelle
  indépendante. `continuous` anime l'état suivi d'un scénario. `sweep` présente
  chaque fichier issu d'une simulation indépendante (lancer la commande sur les
  NPZ successifs, puis assembler les GIF/MP4).

Les trames antérieures au remplissage sont explicitement invalides via
`report_valid`; `report_source` vaut alors `-1`. Chaque trame matérialise ses
`report_phasors`, `report_sequences`, `report_frequency`, `report_rocof` et son
indicateur `report_frequency_valid` (les champs indisponibles valent `NaN`).
La date absolue optionnelle n'intervient jamais dans les calculs.

## Limites métrologiques

L'estimation fréquentielle suppose que l'angle de séquence directe décrit bien la
fréquence commune. Déséquilibre, harmonique, transitoire ou écart important à la
fréquence nominale biaisent le phaseur LS puis sa dérivée. Une faible séquence
directe invalide l'angle et force le remplissage d'une nouvelle fenêtre complète.
La référence de fréquence est dérivée de l'angle déroulé de la séquence directe
théorique ; elle est marquée `NaN` si cette séquence est trop faible ou autour
d'une discontinuité détectée. Le déroulement supprime les sauts de 2π sans rendre
la trajectoire artificiellement monotone.

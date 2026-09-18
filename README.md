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

## Trois expériences pour présentation

Les trois configurations durent 10 s et utilisent **50 trames/s**, `fs=4800 Hz`,
un bruit nul et une graine fixe. Les estimateurs existants sont conservés.

```bash
pmu-sim simulate examples/frequency_variation.json -o results/frequency_variation.npz
pmu-sim simulate examples/phase_unbalance.json -o results/phase_unbalance.npz
pmu-sim simulate examples/balanced_am_fm.json -o results/balanced_am_fm.npz

pmu-sim animate results/frequency_variation.npz -o videos/frequency_variation.mp4 --view frequency --fps 30 --playback-speed 2
pmu-sim animate results/phase_unbalance.npz -o videos/phase_unbalance.mp4 --view imbalance --fps 30 --playback-speed 0.5
pmu-sim animate results/balanced_am_fm.npz -o videos/balanced_am_fm.mp4 --view modulation --fps 30 --playback-speed 1
```

Les durées vidéo sont respectivement **5, 20 et 10 s**. FFmpeg avec `libx264`
doit être accessible dans le PATH. L'export MP4 utilise H.264, `yuv420p` et
`faststart`, avec une image 1536 × 864 adaptée à PowerPoint. Le GIF reste
possible en changeant le suffixe (sa précision temporelle est plus limitée).
Les dossiers de sortie sont créés automatiquement.

Après installation du projet, un lancement groupé équivalent est disponible :

```bash
python scripts/render_experiments.py --fps 30 --speeds 2 0.5 1
```

### Paramètres physiques

- `frequency_variation.json` : rampe de 50 à 51 Hz entre 2 et 8 s. Remplacer
  `frequency` par un profil `step`, `sine` ou `constant` si souhaité.
- `phase_unbalance.json` : angle B de −120° à −100° à `time=4` s, angles A/C
  constants. Chaque entrée d'`angles_deg` accepte les profils existants.
- `balanced_am_fm.json` : un unique profil `amplitudes` est partagé par les
  trois phases. Il suit `value + amplitude*sin(2π*modulation_frequency*t +
  phase_deg*π/180)`. `value=230` V RMS, `amplitude=46` V correspond à une
  profondeur de 20 %. La fréquence commune suit le même type de profil :
  `value=50` Hz, déviation `amplitude=0.5` Hz, modulation à 0.2 Hz. Les angles
  restent 0°, −120°, +120°. Pour un système déséquilibré, la liste historique
  de trois amplitudes/profils reste acceptée.

### Temps et références

Le calcul utilise `fs`; les transmissions sont à `m/reporting_rate`. Le rendu
relit exclusivement le NPZ et ne recalcule aucune simulation. À chaque image,
seules les trames déjà transmises au temps physique atteint sont révélées.
Les courbes utilisent le temps représentatif du phaseur (centre de sa fenêtre),
avec la référence au même instant. La fréquence estimée conserve la convention
et le retard dynamique de l'estimateur existant.

La vidéo comporte `ceil(duration*fps/playback_speed)` images, sans plafond.
L'image n révèle l'état atteint à `min((n+1)*playback_speed/fps, duration)`.
Ainsi le dernier état est toujours visible, et l'écart entre durée encodée et
`duration/playback_speed` est inférieur à une image. Une vitesse élevée peut
sauter des états visuels, sans retirer aucune mesure du NPZ. Une vitesse lente
répète les états reçus sans interpoler de nouvelles mesures PMU.

La phase affichée est celle du synchrophaseur dans le repère nominal `f0`,
en degrés, déroulée à la cadence d'estimation avant sélection des trames.
Les valeurs invalides ne sont pas converties en zéros. Les références se
construisent progressivement comme les estimations.

Sous AM/FM, les séquences **théoriques** V0/V2 sont nulles à la précision
numérique. Le LS à fréquence nominale fixe peut produire une séquence inverse
résiduelle : pour l'exemple fourni, maximum ~1.34 V (0.58 % du nominal).
Le panneau des résidus expose cette erreur ; aucun résultat n'est forcé à zéro.
L'intégration trapézoïdale et la dérivation numérique des références existantes
sont conservées. Un saut d'angle représente un transitoire, pas un saut de la
fréquence porteuse ; la fréquence dérivée à cet instant n'est pas une référence
physique régulière.

`tests/test_experiments.py` vérifie les trois expériences, le calendrier vidéo,
la lecture sans modification des NPZ, l'équilibre théorique et le résidu LS,
le déséquilibre, les références FM et la révélation aux instants de transmission.

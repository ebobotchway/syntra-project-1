# Municipality outlines: attribution

`municipality_outlines.gpkg` is derived from the **Statbel statistical sectors of 1 January 2023**
(Statbel, the Belgian statistical office, https://statbel.fgov.be/en/open-data/statistical-sectors-2023), published under the
**CC BY 4.0** licence (https://creativecommons.org/licenses/by/4.0/).

Changes made: the 19,795 statistical sectors were joined into one outline per municipality (NIS code `CNIS5_2023`) and the outlines were simplified
by 50 m (`scripts/13_prepare_municipality_outlines.py`). Coordinate system: Belgian Lambert 1972 (EPSG:31370).
The original Statbel file is not part of this repository.

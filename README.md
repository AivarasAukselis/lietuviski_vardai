# Lithuanian name filter

A single-page tool for searching 8,954 given names from the Lithuanian register
of citizens' names. Filter by syllable count, by which letters a name may or may
not contain, and by the register's own metadata — then shortlist the names you
like, export them, and load someone else's shortlist back in to see which names
you agree on.

No build step, no dependencies, no network calls. `index.html` contains the
dataset and runs offline.

## What it does

**Letters.** Every one of the 36 characters that occurs in the register gets a
tile showing how many names contain it. Tapping cycles through three states:
any, must have, exclude. Each tile's count makes absences visible — `į` and `ų`
appear in no registered name at all.

**Position-aware exclusions.** An excluded letter can be marked "ok at end",
which permits it as the final character only. Excluding `ė` outright leaves
7,454 names; excluding it everywhere except at the end leaves 8,666, so Eglė and
Saulė survive while Adėlė does not. Active rules are listed under the grid and
can be cleared one at a time.

**Syllables.** Counted from Lithuanian vowel and diphthong structure rather than
looked up, so it works on rare and foreign-origin names too. Vowel runs are
segmented against the diphthongs `ai au ei eu ie ui uo oi ou`; a leading `i`
after a consonant is read as a softening mark rather than a syllable of its own,
which is what makes Liudas two syllables and not three. That last rule is a
toggle, because it goes the wrong way on some borrowed names — Diana counts as
two with it on and three with it off. Treat the numbers as a good approximation,
not an official count.

**Register metadata.** Gender, the Language Commission's verdict on the name
(recommended / discouraged / not recommended), Baltic vs foreign origin, whether
it is a saint's name, and 53 origin categories such as *dvikamienis
asmenvardis*, *graikiškas asmenvardis* or *trumpinys*.

**Layout.** Every active constraint appears as a chip above the results and can
be cleared from there. On a phone the filters live in a slide-over sheet, so the
names are the page rather than something you scroll to.

**Shortlisting.** Tap a name to keep it. Picks are stored per device and reload
with the page; *Clear all filters* leaves them alone. Copy and CSV export
whatever list is on screen, so exporting from the Picked tab gives you just your
shortlist.

**Imported lists.** Any list this page produces can be loaded back in, and each
import becomes a colour. Drop a file anywhere on the page, browse for one, or
paste names straight from Copy. A list can then be set to *must be in* or
*exclude*, so two people who each shortlisted separately can load both files, set
both to *must be in*, and see only the names they agree on — every row shows a
coloured dot per list it belongs to, and *Sort → in most lists* ranks by
agreement. Up to twelve lists at a time; they persist per device like the picks.

Three formats are read: the CSV this page exports (any delimiter; if it carries a
`picked` column that is actually used, only the picked rows are taken), plain
text with one name per line as produced by Copy, and JSON — either `["Eglė",…]`
or `{"label":"…","names":[…]}`.

Imported names are matched against the register exactly, ignoring case. A
spelling that matches nothing is folded to its plain-ASCII form and accepted only
when exactly one register name fits, because the register lists `Egle` and `Eglė`,
`Ruta` and `Rūta` as separate names — guessing between them would quietly change
someone's list. Corrections are reported (`Agate → Agatė`), ambiguous spellings
offer the candidates as buttons, and anything unrecognised is listed rather than
dropped.

## Publishing it

The page is static, so GitHub Pages serves it as-is:

1. Push this repository to GitHub.
2. Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/ (root)`.
3. It goes live at `https://<user>.github.io/<repo>/` within a minute or two.

`index.html` is the whole application. Everything else is provenance.

## Rebuilding from source data

`names.json` and the dataset inlined in `index.html` are generated. `index.html`
is `template.html` with the dataset substituted in, so **edit `template.html`, not
`index.html`**, then rebuild:

```sh
python build.py            # re-inline the committed names.json into index.html
python build.py --check    # fail if index.html is out of date with template.html
```

To rebuild the dataset itself, download *Vardų lingvistiniai duomenys*
([dataset 2664](https://data.gov.lt/datasets/2664/)) as newline-delimited JSON
and run:

```sh
python build.py vardai.jsonl
```

The script derives distinct given names from the register's entries, most of
which are two-name combinations. 8,523 names appear as standalone entries and
carry full catalogue data. A further 431 occur only inside combinations, have no
catalogue data of their own, and are marked *uncatalogued* in the interface with
gender inferred from the combinations they appear in.

Row format in `names.json`:

```
[name, gender, verdict, saint, origin_groups[], subgroups[], subsections[], lookups, catalogued]
  gender    0 unknown · 1 female · 2 male
  verdict   0 uncatalogued · 1 Teiktinas · 2 Vengtinas · 3 Neteiktinas
  origin    1 Baltic · 2 foreign
  subgroups indices into the top-level "pogr" array; subsections into "posk"
  lookups   times the name was searched on the VLKK site
```

## Data source

Names come from the State Commission of the Lithuanian Language (VLKK) register
of citizens' given names — <https://vardai.vlkk.lt> — published as open data on
<https://data.gov.lt>. The register was built from the given names of citizens
in the 2006 Population Register and has been extended with newborns since.

It is not a complete historical record of every name ever registered in
Lithuania. Full alphabetical lists of names and surnames from the Population
Register were prepared for release but blocked by the Ministry of Justice, which
holds the register.

Check the license field on the dataset page before redistributing the data, and
keep the VLKK attribution in place.

## License

The code is MIT licensed (see `LICENSE`). The name data is not covered by that
license and remains subject to the terms of its source.

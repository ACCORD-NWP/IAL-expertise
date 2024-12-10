# IAL expertise

Expert tools to analyse the outputs of IAL configurations.

Each expert is addressing a different kind of output, being able to parse or read these outputs, and compare them to a reference output.

This package has been developped primarily for the needs of [Davai](https://github.com/ACCORD-NWP/DAVAI-tests)
which uses these experts to state on the outputs of tests conducted on a code contribution to IAL
or other associated source repositories.

## Currently implemented experts (non-exhaustive list)

Experts currently are implemented for the following metrics:
* Norms (spectral, gridpoint)
* Fields in FA/GRIB output files
* Jo-tables
* DrHook profiling
* OOPS observation operators, direct and adjoint test
* OOPS model adjoint test
* Bator obscounts, Canari statistics
* Gmkpack build
* Variables printed in model setup

## Expert Board

The analysis and comparison are processed through the use of an ExpertBoard object,
whose class is provided in the package.

## Experts doc generation
Using Vortex's `tbinterface.py`:
```
tbinterface.py -f json -c outputexpert -n ial_expertise
```

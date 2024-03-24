# CHANGELOG

## v1.0.0 (2024-03-24)

### Breaking

* feat(command): add --days option to unused command (#21)

BREAKING CHANGE: DATE positional argument has been converted into an option ([`19424ea`](https://github.com/crabisoft/pdbstore/commit/19424eaff569e9c3cf004bc7678ee7bcd6d3ca75))

### Chore

* chore: update release worklow ([`cbe8de9`](https://github.com/crabisoft/pdbstore/commit/cbe8de9f357f972c9ccc58ea50f97fd7827a9d7e))

### Documentation

* docs: improve documentation (#23) ([`f7b2ba5`](https://github.com/crabisoft/pdbstore/commit/f7b2ba52dc60699f37b77c7baa9afadc4e67a3dc))

### Feature

* feat(command): display total file size for unused command (#22) ([`3d414cb`](https://github.com/crabisoft/pdbstore/commit/3d414cbfa192fa8c0e619a1aea5795e40f7f8074))

## v0.3.0 (2024-03-23)

### Feature

* feat(command): add --dry-run option for del command (#18) ([`99f038a`](https://github.com/crabisoft/pdbstore/commit/99f038a7c404182d8b44d2b33b3971ecdbdc3e09))

* feat(command): add --delete option for unused command (#17) ([`c83851f`](https://github.com/crabisoft/pdbstore/commit/c83851fbe3335343757b445f96552773722c30f6))

### Fix

* fix(transaction): no transaction created if file already exists from … (#19) ([`1754d19`](https://github.com/crabisoft/pdbstore/commit/1754d19153c99006d5d1b61cf55679f319c0934d))

### Unknown

* doc: refactor documentation (#20) ([`c600537`](https://github.com/crabisoft/pdbstore/commit/c600537d6c9b348ecf0004d11a0920cb94979d7d))

## v0.2.0 (2024-03-17)

### Chore

* chore: remove unexpected file ([`08bf34b`](https://github.com/crabisoft/pdbstore/commit/08bf34ba0c43620222e1b4810ee31855d6838437))

* chore: improve makefile (#13) ([`c036350`](https://github.com/crabisoft/pdbstore/commit/c036350db8f34606a12b3fed47338721d700bd94))

### Feature

* feat: add promote command (#15) ([`c66fe2e`](https://github.com/crabisoft/pdbstore/commit/c66fe2eb318ab269a054272b99979af47b73e9c8))

* feat: commit files in parallel (#12) ([`88b5084`](https://github.com/crabisoft/pdbstore/commit/88b5084674a3f477ef8993f87d0bac490edb8a49))

### Test

* test: add dedicated compression test when supported (#14) ([`3b6dfda`](https://github.com/crabisoft/pdbstore/commit/3b6dfdab3eb58d35735d0149d480cc9488548ff6))

### Unknown

* doc: add promote command (#16) ([`c0e5328`](https://github.com/crabisoft/pdbstore/commit/c0e5328e1f725bc7eeac4fc98f802effd51f7bc0))

## v0.1.2 (2024-03-03)

### Fix

* fix: invalid compressed file for huge file (#11) ([`a4c62cc`](https://github.com/crabisoft/pdbstore/commit/a4c62cc80512023473332aad5ff39ef051ca68d5))

## v0.1.1 (2024-02-28)

### Fix

* fix: bad exception management (#10) ([`f5cf7b9`](https://github.com/crabisoft/pdbstore/commit/f5cf7b9efe2ebd99d285c5b1f7f7962469c94f50))

## v0.1.0 (2023-11-24)

### Documentation

* docs: update readme file ([`a43c26d`](https://github.com/crabisoft/pdbstore/commit/a43c26dbb1c9dc796caa977cf5de042f2bdf48f2))

### Feature

* feat: add conda-forge deployment (#9) ([`0357d62`](https://github.com/crabisoft/pdbstore/commit/0357d62be13fb64dbe2acd3564663a10479625be))

* feat: add unused command (#8) ([`23c2450`](https://github.com/crabisoft/pdbstore/commit/23c24500ff5a176eff720dd3ebde7fbd3951773e))

### Fix

* fix: wrong scripts definition from project file (#7) ([`55d9096`](https://github.com/crabisoft/pdbstore/commit/55d9096082acfc36376aff4dd3a8e5852767dc94))

## v0.0.2 (2023-11-09)

### Chore

* chore(ci): improve release workflow (#2) ([`4e47cbc`](https://github.com/crabisoft/pdbstore/commit/4e47cbc276ee14cbc7587ce513d24da669624b78))

### Ci

* ci(actions): improve release workflow (#1) ([`a8f7d60`](https://github.com/crabisoft/pdbstore/commit/a8f7d6000f8c7a200ee25e527c1f7b8fa07841c3))

### Documentation

* docs: update contributing guide (#4) ([`70908ee`](https://github.com/crabisoft/pdbstore/commit/70908ee11a3d8899502fdc5c88ba8713f446589b))

### Fix

* fix(io): need to rename file when decompressing it on windows (#6) ([`676df06`](https://github.com/crabisoft/pdbstore/commit/676df0600364749a031be05d72cd1a0127d55e7c))

### Test

* test: add more tests to improve cover (#5) ([`64347a3`](https://github.com/crabisoft/pdbstore/commit/64347a374c68bb18c75312de94345157bc0296c2))

* test: review tests to improve coverage (#3) ([`c1e211a`](https://github.com/crabisoft/pdbstore/commit/c1e211ac2384b1788a17c5f6d029b3ef9362550a))

## v0.0.1 (2023-10-25)

* Initial release
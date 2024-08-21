# Preface

This directory contains a collection of 100.000 records originating from the post-harvest processing of [Bielefeld Academic Search Engine](https://www.base-search.net/) (BASE). The purpose of this data set is to demonstrate the workings of a software suite created as part of the Master Thesis ["Implementierung einer automatischen DDC-Klassifikation für die Suchmaschine BASE"](https://publiscologne.th-koeln.de/frontdoor/index/index/docId/2513) by [Christoph Broschinski](https://github.com/cbroschinski). To this effect, the data was extracted from a much larger corpus (a so-called "BASE Dump", created on 14/12/2022 with a size of 220.729.544 Records), with the files being specifically selected for containing a large selection of DDC information. While the data is being made available under an Open Database License (see below), the following points should be noted:

- The data represents a snapshot from an older working state of BASE. It will not be updated in the future, nor is it actively maintained by the author or the BASE team.
- While the records can be used to bootstrap and train an Annif backend, the training set is too small to obtain a good classificator for DDC classes. If you are interested in re-using the code with a suitable training set, you might want to get in contact with [BASE](http://oai.base-search.net/#alternatives) and ask for the latest BASE dump.

# License

The data within this directory is made available under the Open Database License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in individual contents of the database are licensed under the Database Contents License: http://opendatacommons.org/licenses/dbcl/1.0/

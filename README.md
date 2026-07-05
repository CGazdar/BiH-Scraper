# BiH-Scraper

## A scraper for around 550 domestic trials in Bosnia and Herzegovina relating to crimes committed during the Yugoslav wars. 

### Authors: **Cyrus Gazdar** _(Simon Fraser University)_, **Adham Bakr** _(On Leave)_


The repository contains 2 models. The first is an AI scraper that didn't get off the ground properly. It's hosted by Ollama and got through the first step of scraping case IDs, but failed to obtain the remaining metadata from the source site. There probably is a way to get this model to work, but I am not paid enough to do it. It is all reproducible via Python, so if you want to try and get it to work, it's all there for you.

The second model is the real one (_Second Scraper_), which contains the source code (_sudbih_scraper.py_), as well as the other tools to translate the CSV once it's created. I haven't replicated the model on my other PC, so I'd recommend first running _diagnose.py_ first to make sure it's all compatible. The model is pretty effective and will give you a lot of really good information about the number of accused, crime location, date, and name of the defendant(s). 

There is one issue with the final model, though: the last column, which is labelled _verdict_result_, doesn't actually give the verdict, but the current model just adds _"there is no information about the verdict."_ This is much harder to obtain and (likely) requires a PDF scraper to get the verdict. Additionally, many of the PDFs on the BiH site are not live but are rather scans, meaning whatever model you use will also need some sort of AI or other tools to read scanned text. I'll make changes to the model when I can find a definitive way to add the verdict. Currently, the closest thing you can get to a current verdict is to look under the _"Execution"_ tab, but this is not necessarily the verdict, as trials are still ongoing and, in other cases, are not made publicly available. It could be a helpful column to add, but for the time being, final verdicts are not going to be part of this CSV.

Information about preliminary installations for the replication will be within the codespace of the second model.

You organize a digital library of comics and manga. You get a list of folder names, one per line, at the end. For each folder, extract its name parts. For each series, give its metadata.

## Naming

For each folder, extract:
- **Series title**: the main name of the series. It can have two parts separated by a hyphen ("First part - Second part"). Numbers at the start or in the middle are part of the title ("100 Bullets"). A number at the end is usually a volume, unless it's a known title that ends in a number ("District 9").
- **Volume** (optional): in formats like "v12", "Tomo 12", "#012" or just the number. If several folders of a series are numbered in sequence, those numbers are volumes.
- **Folder title** (optional): a subtitle for that folder, usually after the volume number.

Rules:
- All folders of the same series must use exactly the same series title, character for character, even if the folder names spell it differently.
- Leave out anything else, such as release or scan group tags. Text in square brackets at the end is usually a release tag.
- Author names never go in the series or folder title. Use them as evidence for the series' writer.
- Use the conventional capitalization of the title's language, and restore missing accents ("Dia" -> "día"). English uses title case, with articles and short prepositions lowercased ("Call of the Night"). Spanish only capitalizes the first word and proper nouns ("Un título de la serie").

## Series metadata

Give one `series` item per series, not per folder, with the series title exactly as in the entries.
- Writer, penciller and genre describe the work itself, so they're the same in every edition. Give them even if you can't find the publisher.
- Write Japanese names in Western order (given name first) and without macrons, as printed in Western editions: "Naoki Urasawa", "Goro Taniguchi".
- {country}
- If you don't know a value, use null. Never guess.
- For genre, pick one or more from: {genres}. Also add one demographic, when one applies: {demographics}.

## Notes

Both entries and series items have `notes`: a short remark shown to the user, so they know what to double-check. Use it only when you made a tough call and another reading is plausible (e.g. unsure whether some text is an author or a folder title, or a publisher you couldn't confirm). For clear cases, which should be most of them, it must be null. Don't add notes just to describe what you did.

For a series item where writer, penciller or genre is null, the note must say which case it is: you don't know the series at all, or you know the work but not the local edition. If a genre comes only from words in the title, say so.

## Examples

- `Call Of The Night 11-Kotoyama [asdfg]` -> series "Call of the Night", volume 11, no title. "Kotoyama" is the author, "[asdfg]" a release tag.
- `Lobo Solitario 14 - El Dia de la Purificacion [aaaa]` -> series "Lobo solitario", volume 14, title "El día de la purificación". Spanish capitalization, accents restored.
- `Asadora #008 - Naoki Urasawa [fdgfdgfd]` -> series "Asadora", volume 8, no title. "Naoki Urasawa" is the author.

Series item for the first example, for an edition published in Argentina:
`{"series": "Call of the Night", "writer": "Kotoyama", "penciller": "Kotoyama", "publisher": "Ivrea", "imprint": null, "genre": ["Romance", "Supernatural", "Shounen"], "notes": null}`

## Folders

{folders}

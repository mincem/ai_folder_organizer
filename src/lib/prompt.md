You are an expert in parsing and reformatting folder names for a digital library. Your task is to extract specific attributes from a given list of folder names and then reformat them according to a strict pattern.

For each folder name provided, you must identify and extract the following attributes:
- **Series Title**: This is the primary name of the series. It can have two parts separated by a hyphen (e.g., "First part - Second part"). Numbers at the beginning or in the middle of a title are generally part of the title (e.g., "100 Bullets," "District 9"). However, a number at the *end* of a title is usually a volume number unless it's a known, specific title that includes a trailing number (e.g., "District 9" is an exception, but "Some Series 1" would imply a volume).
- **Volume Number** (optional): This indicates the specific volume within a series. It can appear in various formats, including but not limited to: "v{{number}}", "Tomo {{number}}", "#{{number}}", or simply the number itself. If a series has multiple folders that are numerically sequential (e.g., "Some Series 1 - Author" and "Some Series 2 - Author"), these numbers should be interpreted as volume numbers and the series title should be consistent (e.g., "Some Series").
- **Folder Title** (optional): This is a specific subtitle or descriptor for that particular folder, usually appearing *after* the volume number (if present). Any text enclosed in square brackets `[]` at the end of the folder name should be considered part of the folder title and not part of the series or volume.

**Important Considerations:**
* **Ignore Authors and Extraneous Information**: Disregard any information that does not fit the defined attributes, such as author names or other descriptive text that isn't clearly a folder title.
* **Special Characters**: Filenames must be Windows-compatible, so special characters like `:` and `*` should be replaced with a hyphen `-` or removed as appropriate.
* **Spanish Titles Capitalization**: For titles identified as Spanish, only the first word should be capitalized. Subsequent words should be in lowercase unless they are proper nouns (e.g., "Un título de la serie" instead of "Un Título De La Serie").
* **Example Handling**:
    * `Call Of The Night 11-Kotoyama [asdfg]` -> `Call of the Night v11` (Author "Kotoyama" and bracketed text `[asdfg]` are ignored. "Of The" is lowercased.)
    * `Lobo Solitario 14 - El Dia de la Purificacion [aaaa]` -> `Lobo solitario v14 - El día de la purificación` (Spanish capitalization rule applied. Bracketed text `[aaaa]` is ignored.)
    * `Asadora #008 - Naoki Urasawa [fdgfdgfd]` -> `Asadora v08` (Author "Naoki Urasawa" and bracketed text `[fdgfdgfd]` are ignored.)

**Output Format:**
Reformat each folder name into the following strict pattern: `'{{series title}} v{{volume as two-digit number}} [{{folder title}}]'`.

* If a volume number is present, it **must** be formatted as a two-digit number (e.g., "v01", "v12").
* If an attribute is missing (e.g., no volume or no folder title), skip that part of the pattern. A valid result can be just `{{series title}}` if no other attributes are found.
* The square brackets `[]` around the folder title should only be included if a folder title is present.

Your final answer must be a JSON array of pairs, where each pair is `[original_name, new_name]`. Ensure all generated pairs are valid JSON. You must not respond with Python code. You must respond in the format specified above. 

Here is the list of folder names to process:

---
id: 0
slug: language-parameter
status: done
branch: feature/language-parameter
created: 2026-03-12T11:00:00-07:00
concluded: 2026-03-12T12:00:00-07:00
pr: https://github.com/gitronald/suggests/pull/9
---

# Add language parameter

Add language parameter support for Google and Bing autocomplete APIs.

Cherry-picked from [jueri/suggests](https://github.com/jueri/suggests) (`44e5b4e`), then reviewed and extended:

- Add `hl` param for Google language (e.g. `'es'`, `'de'`) and `mkt` param for Bing market (e.g. `'es-es'`, `'de-de'`)
- Pass language params through `get_suggests`, `requester`, and `get_suggests_tree`
- Use `response.text` for encoding-aware decoding (Google returns `charset=ISO-8859-1`)
- URL-encode all API parameters via `urllib.parse.urlencode`
- Remove `sclient` from public API (hardcoded in `get_google_url`)
- Update README with usage examples for both sources

# Log

## Code Review

Launched parallel agents to review the fork commit from three angles: API design, encoding/parsing, and security/robustness.

### Major (fixed)
1. **Latin-1 decode** — replaced `response.content.decode('latin-1')` with `response.text` which respects the Content-Type header
2. **`get_suggests_tree` missing params** — language params now pass through the full call chain
3. **URL injection** — switched from f-string interpolation to `urllib.parse.urlencode`

### Moderate (fixed)
4. **Redundant default handling** — removed interior falsy-guards, defaults set at each layer
5. **Bing language support** — added `mkt` parameter for Bing market codes

### Minor (fixed)
6. **`hl` naming** — kept `hl` for Google (matches API), added `mkt` for Bing (matches API)
7. **Missing docstrings** — added for all new parameters

## Test Results

### Google (Spanish)
```python
>>> s = suggests.get_suggests('los gansos son ', source='google', hl='es')
>>> s['suggests']
['los gansos son territoriales', 'los gansos son monogamos', 'los gansos son patos', 'los gansos son comestibles', 'los gansos son aves']
```

### Bing (Spanish)
```python
>>> s = suggests.get_suggests('los gansos son ', source='bing', mkt='es-es')
>>> s['suggests']
['los gansos son agresivos', 'que son los gansos', 'sonidos de gansos']
```

### get_suggests_tree (German)
```
Tree size: 11
  [0] Gänse sind : ['gänse sind die besseren wachhunde', 'gänse sind zugvögel']
  [1] gänse sind die besseren wachhunde: ['gänse sind die besseren wachhunde', 'gänse wachhund']
  [1] gänse sind zugvögel: ['gänse sind zugvögel', 'welche gänse sind zugvögel']
```

# Retrospective

- Google returns `charset=ISO-8859-1`, not UTF-8 — `response.text` handles this automatically
- Using separate `hl`/`mkt` params (matching each API's naming) is cleaner than a unified `lang` param that needs format validation per source
- `sclient` value matters for Google (only `psy-ab` returns parseable JSON) but doesn't need to be user-configurable

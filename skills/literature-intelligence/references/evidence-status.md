# Evidence status

| Status | Meaning | Allowed verification |
|---|---|---|
| `candidate` | Lead recorded, content unavailable | metadata unverified; content unavailable |
| `retrieved` | Hash-addressed bytes are available | metadata unverified; content unverified |
| `screened` | Inclusion decision and reason recorded | content still unverified |
| `verified_metadata` | Bibliographic identity checked | metadata verified; content not verified |
| `verified_content` | Current content inspected for claim support | metadata and content verified |
| `excluded` | Source excluded with a reason | decision must be exclude |

Metadata verification and content verification answer different questions. A correct title, DOI,
or author list does not show that a source supports a claim. Conversely, a local text may be
content-inspected while publication metadata remains unavailable; it must not be labeled
`verified_content` under the V1 combined terminal status.

The SHA-256 value locks provenance to specific bytes. When the bytes change, any content
verification and claim links become stale until they are inspected again. Provider responses
enter as candidates; no provider may automatically promote them to verified evidence.

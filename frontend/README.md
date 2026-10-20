# Preference Grammar Frontend

React/Vite UI for the corrected Preference Grammar workflow.

The frontend collects:

- optional audio evidence metadata,
- target word,
- candidate IPA variants and counts,
- optional international reference IPA,
- ranked PG tenets.

It sends the payload to `POST /preference/analyze` on the backend and displays
the operability table plus preferred pronunciation.

## Development

```bash
npm install
npm run dev
```

Default backend URL:

```env
VITE_API_BASE_URL=http://localhost:8001
```

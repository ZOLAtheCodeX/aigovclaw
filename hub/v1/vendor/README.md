# v1 vendor directory

Drop two files here to enable v1 generation:

- `react.production.min.js` from https://unpkg.com/react@18/umd/react.production.min.js
- `react-dom.production.min.js` from https://unpkg.com/react-dom@18/umd/react-dom.production.min.js

Download offline, verify integrity, commit. The generator never fetches over
the network.

Until these files are dropped, `python3 -m aigovclaw.hub.v1.cli generate`
exits with a clear error.

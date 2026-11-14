# Shorty for Dify

[Shorty](https://aishorty.com) summarizes YouTube videos and web pages and transcribes audio and video. This plugin lets Dify agents, workflows and chatflows call Shorty and use the result.

**Author:** aishorty (Devino Solutions) · **Source:** https://github.com/DevinoSolutions/dify-plugin-shorty · **Contact:** hello@devino.ca

## Tools

| Tool | What it does |
| --- | --- |
| **Summarize YouTube Video** | A structured summary (title and sections) of a YouTube video. |
| **Summarize Web Page** | A structured summary of a public web page or article. |
| **Transcribe Audio or Video** | The text and timed segments of an audio or video file from a direct link (.mp3, .wav, .mp4 and so on). YouTube links are not transcribed; use the summarize tool for those. |
| **Get Job Result** | Fetches the result of a job that was still running when another tool returned. |

Shorty works in jobs. Each tool starts a job, waits for it (up to the "Max wait" setting, 240 seconds for summaries and 480 for transcripts by default) and returns the result as Markdown or text plus a JSON message for workflow variables. If the job is not finished in time, the tool returns the job id and you can fetch the result later with Get Job Result.

## Setup

1. Create an account at [aishorty.com](https://aishorty.com) and create an API key under Settings, API Keys.
2. In Dify, install the **Shorty** plugin.
3. Open **Tools, Shorty, Authorize** and paste the API key. Dify checks it with a request that costs nothing.
4. Add the tools to an agent, a workflow or a chatflow.

## Requirements and connection

- Dify 1.0.0 or later.
- Connection: outbound HTTPS access to `aishorty.com` from the Dify plugin daemon.
- A Shorty API key. The Free plan works; limits and quotas are listed at [aishorty.com/docs/pricing](https://aishorty.com/docs/pricing).

## Privacy

See [PRIVACY.md](PRIVACY.md).

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/pytest
```

Package with Dify's plugin CLI: `dify plugin package .`

## License

MIT, see [LICENSE](LICENSE).

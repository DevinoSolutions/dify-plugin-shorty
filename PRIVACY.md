# Privacy policy

This plugin is published by Devino Solutions (https://aishorty.com), the company that runs Shorty.

## What the plugin sends

When a tool runs, the plugin sends the link you give it (a YouTube link, a web page link or an audio or video file link), the language settings you choose and, for the Get Job Result tool, a job id to the Shorty API at `https://aishorty.com/v1`. Your Shorty API key goes in the `Authorization` header of each request. When you save the API key in Dify, the plugin checks it with one request to `GET /v1/usage`, which costs nothing.

The plugin calls no other host.

## What the plugin stores

The plugin stores nothing. It keeps no logs, files or caches. Dify stores the API key you enter, as it does for every plugin credential.

## What Shorty does with the data

Shorty fetches the link you submitted, creates the summary or transcript and keeps the result in your Shorty account. The plugin returns the result to Dify. Shorty counts the request against your plan. See the Shorty privacy policy: https://aishorty.com/privacy

## Contact

hello@devino.ca

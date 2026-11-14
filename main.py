from dify_plugin import DifyPluginEnv, Plugin

# Transcription jobs can take a few minutes, and the tools wait for them.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=600))

if __name__ == "__main__":
    plugin.run()

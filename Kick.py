import re, json, requests
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HLSStream

@pluginmatcher(re.compile(
    r'https?://kick\.com/(?:video/(?P<video_no>[a-f0-9-]+)|(?P<channel_id>[^/?]+))$',
))
class KickPlugin(Plugin):
    LIVE_INFO = "https://kick.com/api/v2/channels/{channel_id}/livestream"
    VOD_INFO = "https://kick.com/api/v1/video/{video_no}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}


    def _get_streams(self):
        channel_id = self.match.group("channel_id")
        video_no = self.match.group("video_no")

        if channel_id:
            return self._get_live_streams(channel_id)
        elif video_no:
            return self._get_vod_streams(video_no)
        
    def _get_live_streams(self, channel_id):
        api_url = self.LIVE_INFO.format(channel_id=channel_id)

        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error("Failed to fetch channel information: {0}".format(str(e)))
            return

        if response.status_code == 404:
            self.logger.error("Channel not found")
            return

        try:
            data = response.json().get('data', {})
            if data is None:
                self.logger.error("Channel is not live or not found")
                return

            self.author = channel_id
            self.category = data.get('category').get('slug')
            self.title = data.get('session_title')
            stream_url = data.get('playback_url')

            yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()

        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON response: {0}".format(str(e)))
            return
        
    def _get_vod_streams(self, video_no):
        api_url = self.VOD_INFO.format(video_no=video_no)

        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error("Failed to fetch video information: {0}".format(str(e)))
            return

        if response.status_code == 404:
            self.logger.error("Video not found")
            return
        
        try:
            content = response.json().get('livestream', {})
            video_url = response.json().get('source')

            self.author = content.get('channel').get('slug')
            self.category = content.get('categories', [])[0].get('slug')
            self.title = content.get('session_title')
            
            yield from HLSStream.parse_variant_playlist(self.session, video_url).items()

        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON response: {0}".format(str(e)))
            return

__plugin__ = KickPlugin

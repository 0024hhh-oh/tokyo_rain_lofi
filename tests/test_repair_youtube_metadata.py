import copy
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from repair_youtube_metadata import clean_metadata, repair_video
from youtube_titles import generate_youtube_title, generate_youtube_description

UUID = 'C46F9275 4F43 4E3C 8A47 B8A1C7205A16'
TITLE = f'【Playlist】Tokyo Rainy Night Memories | copy {UUID}【LOFI】【CHILL】【BGM】'
DESCRIPTION = generate_youtube_description('night', 'Batch25', ['background.png']).replace('the quiet streets of Tokyo on a rainy night', f'copy {UUID} on a rainy Tokyo night')


def test_exact_production_failure():
    assert clean_metadata(TITLE, DESCRIPTION) == (generate_youtube_title('night', 'Batch25', ['background.png']), generate_youtube_description('night', 'Batch25', ['background.png']))


def test_unrelated_video_and_valid_metadata_are_unchanged():
    assert clean_metadata('Other video', DESCRIPTION) == ('Other video', DESCRIPTION)
    assert clean_metadata('【Playlist】Tokyo Memory Archive | Kanda【LOFI】【CHILL】【BGM】', 'Original text') == ('【Playlist】Tokyo Memory Archive | Kanda【LOFI】【CHILL】【BGM】', 'Original text')


def test_update_preserves_other_snippet_fields_and_verifies(tmp_path):
    current = {'id': 'yJIgSTG9uuc', 'snippet': {'title': TITLE, 'description': DESCRIPTION, 'categoryId': '10', 'tags': ['lofi'], 'defaultLanguage': 'en', 'defaultAudioLanguage': 'en', 'channelId': 'channel'}}
    updates = []
    def list_video(**kwargs):
        assert kwargs == {'part': 'snippet', 'id': current['id']}
        return SimpleNamespace(execute=lambda: {'items': [copy.deepcopy(current)]})
    def update_video(**kwargs):
        assert kwargs['part'] == 'snippet'
        assert 'status' not in kwargs['body']
        assert 'channelId' not in kwargs['body']['snippet']
        updates.append(kwargs['body'])
        current['snippet'].update(kwargs['body']['snippet'])
        return SimpleNamespace(execute=lambda: current)
    youtube = SimpleNamespace(videos=lambda: SimpleNamespace(list=list_video, update=update_video))
    assert repair_video(youtube, current['id'], True, tmp_path)
    assert updates[0]['snippet']['tags'] == ['lofi']
    assert updates[0]['snippet']['categoryId'] == '10'
    assert (tmp_path / 'yJIgSTG9uuc.json').exists()
    assert not repair_video(youtube, current['id'], True, tmp_path)

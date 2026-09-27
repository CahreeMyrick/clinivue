import base64
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr

from PIL import Image

from example_vlm import main, build_request, candidate_prompts, encode_image, parse_result


def sample_result():
    return {
        'image_assessment': {'modality': 'X-ray', 'view': 'unknown', 'quality': 'test', 'limitations': []},
        'summary': 'Synthetic test response, not an image interpretation.',
        'entities': [{
            'name': 'opacity', 'category': 'finding', 'status': 'uncertain',
            'location': 'lung', 'laterality': 'unknown', 'appearance': 'test',
            'evidence': 'test', 'certainty': 'low', 'possible_interpretations': [],
            'localization_prompt': 'lung opacity',
        }],
        'unanswered_questions': [],
    }


class VLMTests(unittest.TestCase):
    def test_full_image_is_encoded_without_crop(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.png'
            Image.new('RGB', (600, 800), 'white').save(path)
            url, metadata = encode_image(path, 400)
            encoded = base64.b64decode(url.split(',', 1)[1])
            self.assertEqual(Image.open(BytesIO(encoded)).size, (300, 400))
            self.assertEqual(metadata['original_size'], [600, 800])
            payload = build_request('test-model', 'Extract entities', url, 1024)
            self.assertEqual(payload['messages'][0]['content'][1]['image_url']['url'], url)
            self.assertNotIn('response_format', payload)

    def test_fenced_json_and_invalid_entities(self):
        result = sample_result()
        self.assertEqual(parse_result('```json\n' + json.dumps(result) + '\n```'), result)
        result['entities'][0]['status'] = 'probably'
        with self.assertRaisesRegex(ValueError, 'invalid status'):
            parse_result(json.dumps(result))
        with self.assertRaises(ValueError):
            parse_result('{"entities": []}')

    def test_cli_saves_valid_and_truncated_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'image.png'
            Image.new('RGB', (32, 32)).save(image)
            output = Path(directory) / 'result.json'
            for finish_reason, expected_code in [('stop', 0), ('length', 1)]:
                response = {'choices': [{'finish_reason': finish_reason,
                            'message': {'content': json.dumps(sample_result())}}]}
                with patch('sys.argv', ['example_vlm.py', str(image), '--model', 'test',
                                       '--output', str(output)]), \
                     patch('example_vlm.urlopen', return_value=BytesIO(json.dumps(response).encode())), \
                     redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertEqual(main(), expected_code)
                record = json.loads(output.read_text())
                self.assertEqual(record['response'], response)
                self.assertEqual('parse_error' in record, finish_reason == 'length')

    def test_prompts_exclude_absence_and_anatomy_and_deduplicate(self):
        result = sample_result()
        entity = result['entities'][0]
        result['entities'].extend([dict(entity), dict(entity, status='absent'),
                                   dict(entity, category='anatomy', localization_prompt='heart')])
        self.assertEqual(candidate_prompts(result), ['lung opacity'])


if __name__ == '__main__':
    unittest.main()

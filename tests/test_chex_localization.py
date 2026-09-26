import unittest
from unittest.mock import Mock

import torch
from PIL import Image

from chex_localization import CheXLocalizationService, boxes_to_original


class LocalizationTests(unittest.TestCase):
    def test_crop_coordinates_land_on_original_image(self):
        full_crop = torch.tensor([[0.5, 0.5, 1., 1.]])
        torch.testing.assert_close(boxes_to_original(full_crop, (600, 800)),
                                   torch.tensor([[0., 100., 600., 700.]]))
        torch.testing.assert_close(boxes_to_original(full_crop, (801, 600)),
                                   torch.tensor([[100., 0., 700., 600.]]))

    def test_filtering_and_prompt_association(self):
        service = CheXLocalizationService(threshold=0.5)
        result = Mock()
        result.multiboxes = torch.tensor([[[[.5, .5, .5, .5], [.5, .5, 0., .5]],
                                           [[.5, .5, 1., 1.], [.5, .5, .5, .5]]]])
        result.multiboxes_weights = torch.tensor([[[.8, .9], [.2, .7]]])
        service.model = {'img_encoder': Mock(), 'txt_encoder': Mock(),
                         'detector': Mock(return_value=result)}
        detections = service.localize_many(Image.new('RGB', (600, 800)), ['a', 'b'])
        self.assertEqual([d['label'] for d in detections], ['a', 'b'])
        self.assertEqual(detections[0]['box'], [150., 250., 450., 550.])
        pixels = service.model['img_encoder'].call_args.args[0]
        self.assertEqual(tuple(pixels.shape), (1, 224, 224))
        self.assertAlmostEqual(pixels[0, 0, 0].item(), -0.505 / 0.248, places=5)

    def test_missing_checkpoint_has_actionable_error(self):
        with self.assertRaisesRegex(FileNotFoundError, '--chex-checkpoint'):
            CheXLocalizationService('/nonexistent/checkpoint.pth').load()


if __name__ == '__main__':
    unittest.main()

#exports a trained Piper voice checkpoint to the .onnx format used for
#inference (the format tts_piper.py loads).
#
#uses the legacy torch.onnx exporter (dynamo=False): this model's normalizing-
#flow layers have data-dependent branching that the newer torch.export-based
#exporter can't trace.
import argparse
import logging
from pathlib import Path
from typing import Optional

import torch

from piper.train.vits.lightning import VitsModel

_LOGGER = logging.getLogger(__name__)
OPSET_VERSION = 15


def main() -> None:
    torch.manual_seed(1234)

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_path = Path(args.checkpoint)
    model = VitsModel.load_from_checkpoint(checkpoint_path, map_location="cpu")
    model_g = model.model_g
    model_g.eval()

    with torch.no_grad():
        model_g.dec.remove_weight_norm()

    def infer_forward(text, text_lengths, scales, sid=None):
        noise_scale = scales[0]
        length_scale = scales[1]
        noise_scale_w = scales[2]
        audio = model_g.infer(
            text,
            text_lengths,
            noise_scale=noise_scale,
            length_scale=length_scale,
            noise_scale_w=noise_scale_w,
            sid=sid,
        )[0].unsqueeze(1)
        return audio

    model_g.forward = infer_forward

    num_symbols = model_g.n_vocab
    num_speakers = model_g.n_speakers

    dummy_input_length = 50
    sequences = torch.randint(
        low=0, high=num_symbols, size=(1, dummy_input_length), dtype=torch.long
    )
    sequence_lengths = torch.LongTensor([sequences.size(1)])

    sid: Optional[torch.LongTensor] = None
    if num_speakers > 1:
        sid = torch.LongTensor([0])

    scales = torch.FloatTensor([0.667, 1.0, 0.8])
    dummy_input = (sequences, sequence_lengths, scales, sid)

    torch.onnx.export(
        model=model_g,
        args=dummy_input,
        f=str(output_path),
        verbose=False,
        opset_version=OPSET_VERSION,
        input_names=["input", "input_lengths", "scales", "sid"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size", 1: "phonemes"},
            "input_lengths": {0: "batch_size"},
            "output": {0: "batch_size", 2: "time"},
        },
        dynamo=False,
    )
    _LOGGER.info("Exported model to %s", output_path)


if __name__ == "__main__":
    main()

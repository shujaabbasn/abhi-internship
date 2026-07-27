#fine-tunes the Urdu Piper voice on banking-domain recordings, resuming from
#an existing checkpoint rather than training from scratch.
#
#uses a single checkpoint-saving callback based on val_mel (mel-spectrogram
#reconstruction error), since it's always logged during training. val_mos
#(a perceptual quality score) needs an external prediction model downloaded
#on first use and isn't reliable enough on this setup to depend on.
import logging
from lightning.pytorch.callbacks import ModelCheckpoint
from piper.train.__main__ import VitsLightningCLI
from piper.train.vits.dataset import VitsDataModule
from piper.train.vits.lightning import VitsModel

logging.basicConfig(level=logging.INFO)

_CALLBACKS = [
    ModelCheckpoint(
        monitor="val_mel",
        mode="min",
        save_top_k=5,
        save_last=True,
        filename="epoch={epoch}-val_mel={val_mel:.4f}",
        auto_insert_metric_name=False,
    ),
]

if __name__ == "__main__":
    VitsLightningCLI(
        VitsModel,
        VitsDataModule,
        trainer_defaults={"max_epochs": -1, "callbacks": _CALLBACKS},
    )

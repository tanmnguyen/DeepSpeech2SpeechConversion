import os 
import torch 
import configs 
import argparse 

import torch.optim as optim
from torch.utils.data import DataLoader
from WordTokenizer import word_tokenizer
from configs import speech_recognition_cfg 
from utils.batch import speech_recognition_collate_fn
from datasets.ASRMelSpecDataset import ASRMelSpecDataset
from models.SpeechRecognitionModel import SpeechRecognitionModel

from utils.steps import train_net, valid_net
from tqdm import tqdm


def main(args):
    # load word tokenizer
    word_tokenizer.load(os.path.join(args.data, "lang_nosp", "words.txt"))

    hparams = {
        "n_cnn_layers": 3,
        "rescnn_strides": [1, 2, 2],
        "n_rnn_layers": 5,
        "rnn_dim": 512,
        "n_class": len(word_tokenizer),
        "n_feats": 128,
        "stride":2,
        "dropout": 0.1,
        "blank": word_tokenizer.word2idx[word_tokenizer.PAD],
        "learning_rate": configs.speech_recognition_cfg['learning_rate'],
        "batch_size": configs.speech_recognition_cfg['batch_size'],
        "epochs": configs.speech_recognition_cfg['epochs']
    }
    
    train_dataset = ASRMelSpecDataset(os.path.join(args.data, "train"))
    valid_dataset = ASRMelSpecDataset(os.path.join(args.data, "dev"))

    train_dataloader = DataLoader(
        train_dataset, 
        batch_size=hparams['batch_size'],
        collate_fn=speech_recognition_collate_fn, 
        shuffle=True
    )

    valid_dataloader = DataLoader(
        valid_dataset, 
        batch_size=hparams['batch_size'],
        collate_fn=speech_recognition_collate_fn, 
        shuffle=False
    )

    model = SpeechRecognitionModel(
        n_cnn_layers=hparams['n_cnn_layers'], 
        rescnn_strides=hparams['rescnn_strides'],
        n_rnn_layers=hparams['n_rnn_layers'], 
        rnn_dim=hparams['rnn_dim'],
        n_class=hparams['n_class'], 
        n_feats=hparams['n_feats'], 
        blank=hparams["blank"], 
        stride=hparams['stride'], 
        dropout=hparams['dropout']
    ).to(configs.device)

    print(model)
    print("Device: ", configs.device)
    print("Number of parameters: ", sum(p.numel() for p in model.parameters()))

    optimizer = optim.AdamW(model.parameters(), hparams['learning_rate'])
    scheduler = optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=hparams['learning_rate'],
        steps_per_epoch=int(len(train_dataloader)),
        epochs=hparams['epochs'],
        anneal_strategy='linear'
    )


    train_history, valid_history = [], [] 
    for epoch in range(hparams['epochs']):
        train_history.append(train_net(model, train_dataloader, optimizer, scheduler))
        print(
            f"[Train] Epoch: {epoch+1}/{hparams['epochs']} - " + 
            f"Loss: {train_history[-1]['loss']} | " + 
            f"WER: {train_history[-1]['wer']} | " + 
            f"SER: {train_history[-1]['ser']}"
        )

        valid_history.append(valid_net(model, valid_dataloader))
        print(
            f"[Valid] Epoch: {epoch+1}/{hparams['epochs']} - " + 
            f"Loss: {valid_history[-1]['loss']} | " + 
            f"WER: {valid_history[-1]['wer']} | " + 
            f"SER: {valid_history[-1]['ser']}"
        )
        break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('-data',
                        '--data',
                        required=True,
                        help="path to kaldi data format directory. This should contains dev, test, and train folders")


    args = parser.parse_args()
    main(args)
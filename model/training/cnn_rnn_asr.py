import torch
import torch.nn as nn

class CNNRNNASR(nn.Module):
    def __init__(self, input_dim, num_phonemes):
        super(CNNRNNASR, self).__init__()
        self.conv1 = nn.Conv1d(input_dim, 128, kernel_size=5, padding=2)
        self.pool1 = nn.MaxPool1d(kernel_size=2)
        self.conv2 = nn.Conv1d(128, 256, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool1d(kernel_size=2)
        self.lstm = nn.LSTM(256, 256, num_layers=2, bidirectional=True, batch_first=True, dropout=0.3)
        self.fc = nn.Linear(512, num_phonemes + 1)  # +1 for CTC blank token

    def forward(self, x):
        x = self.conv1(x)
        x = torch.relu(x)
        x = self.pool1(x)
        x = self.conv2(x)
        x = torch.relu(x)
        x = self.pool2(x)
        x = x.permute(0, 2, 1)  # (batch, time, features)
        x, _ = self.lstm(x)
        x = self.fc(x)
        return x

# Hyperparameters
input_dim = 40  # Number of MFCC features
num_phonemes = 50  # Example phoneme count

# Instantiate the model
asr_model = CNNRNNASR(input_dim, num_phonemes)
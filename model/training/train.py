import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from model.preprocessing.data_loader import load_dataset
from model.training.cnn_rnn_asr import asr_model

# Load dataset
train_data = [("audio1.wav", "phoneme1"), ("audio2.wav", "phoneme2")]
X_train, y_train = load_dataset(train_data)

# Convert data to PyTorch tensors
X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.int32)

# Create DataLoader
train_dataset = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# Define loss function and optimizer
criterion = nn.CTCLoss(blank=0)
optimizer = optim.Adam(asr_model.parameters(), lr=0.001)

# Training loop
num_epochs = 20
for epoch in range(num_epochs):
    asr_model.train()
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        outputs = asr_model(X_batch)
        input_lengths = torch.full((outputs.size(0),), outputs.size(1), dtype=torch.long)
        target_lengths = torch.full((y_batch.size(0),), y_batch.size(1), dtype=torch.long)
        loss = criterion(outputs.log_softmax(2), y_batch, input_lengths, target_lengths)
        loss.backward()
        optimizer.step()
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {loss.item()}")

# Save model
torch.save(asr_model.state_dict(), "asr_model.pth")
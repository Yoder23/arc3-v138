"""Trainable temporal predictors: conventional, liquid-inspired, spiking and hybrid."""
import torch
from torch import nn
import torch.nn.functional as F


class Spike(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x):
        ctx.save_for_backward(x)
        return (x > 0).to(x.dtype)

    @staticmethod
    def backward(ctx, g):
        x, = ctx.saved_tensors
        return g/(1+4*x.abs()).square()


class Brain(nn.Module):
    def __init__(self, kind, hidden=40):
        super().__init__(); self.kind = kind; self.hidden = hidden
        if kind == 'gru':
            self.cell = nn.GRUCell(20, hidden)
        elif kind == 'liquid':
            self.candidate = nn.Linear(20+hidden, hidden)
            self.rate = nn.Linear(20+hidden, hidden)
        elif kind in ('spiking', 'hybrid'):
            self.current = nn.Linear(20+hidden, hidden)
            self.decay = nn.Parameter(torch.zeros(hidden))
            self.threshold = nn.Parameter(torch.full((hidden,), -.7))
            nn.init.constant_(self.current.bias, .4)
            if kind == 'hybrid':
                self.candidate = nn.Linear(20+2*hidden, hidden)
                self.rate = nn.Linear(20+2*hidden, hidden)
        else:
            raise ValueError(kind)
        self.readout = nn.Sequential(nn.Linear(hidden+3, hidden), nn.Tanh(), nn.Linear(hidden, 18))

    def initial(self, batch):
        z = next(self.parameters()).new_zeros(batch, self.hidden)
        if self.kind in ('spiking', 'hybrid'):
            return (z, z.clone(), z.clone(), z.clone())
        return z

    def step(self, x, state):
        dt = x[:, -2:-1].clamp(.05, 2)
        if self.kind == 'gru':
            state = self.cell(x, state); h = state
        elif self.kind == 'liquid':
            joined = torch.cat((x, state), -1)
            alpha = 1-torch.exp(-dt*(F.softplus(self.rate(joined))+.05))
            state = state + alpha*(torch.tanh(self.candidate(joined))-state); h = state
        else:
            v, spikes, rate, liquid = state
            beta = torch.exp(-dt*F.softplus(self.decay))
            current = self.current(torch.cat((x, spikes), -1))
            voltage = beta*v + (1-beta)*current
            threshold = F.softplus(self.threshold)
            spikes = Spike.apply(voltage-threshold)
            v = voltage-spikes.detach()*threshold
            rate = .7*rate+.3*spikes
            if self.kind == 'hybrid':
                joined = torch.cat((x, rate, liquid), -1)
                alpha = 1-torch.exp(-dt*(F.softplus(self.rate(joined))+.05))
                liquid = liquid+alpha*(torch.tanh(self.candidate(joined))-liquid)
                h = liquid
            else:
                h = rate
            state = (v, spikes, rate, liquid)
        predictions = 4*self.readout(torch.cat((h, x[:, :3]), -1)).reshape(-1,6,3)
        return predictions, state

    def forward(self, x):
        state = self.initial(len(x)); outputs=[]
        for t in range(x.shape[1]):
            pred, state = self.step(x[:,t], state); outputs.append(pred)
        return torch.stack(outputs, 1)

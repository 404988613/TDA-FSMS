import torch
import torch.nn as nn

class SupConLoss(nn.Module):

    def __init__(self, temperature=0.07):
        super(SupConLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features, labels=None, mask=None):
        device = (torch.device('cuda')
                  if features.is_cuda
                  else torch.device('cpu'))

        batch_size = features.shape[0]  ## 2*N

        if labels is not None and mask is not None:
            raise ValueError('Cannot define both `labels` and `mask`')
        elif labels is None and mask is None:
            mask = torch.eye(batch_size, dtype=torch.float32).to(device)
        elif labels is not None:
            labels = labels.contiguous().view(-1, 1)
            if labels.shape[0] != batch_size:
                raise ValueError('Num of labels does not match num of features')
            mask = torch.eq(labels, labels.T).float().to(device)
            unmask = 1-mask
        else:
            mask = mask.float().to(device)

        contrast_feature = features
        anchor_feature = contrast_feature
        anchor_count = 2 ## we have two views

        # compute logits
        anchor_dot_contrast = torch.div(
            torch.matmul(anchor_feature, contrast_feature.T),
            self.temperature) # div:对应元素相除 matmul:矩阵相乘

        logits_mask = torch.scatter(torch.ones_like(mask), 1, torch.arange(batch_size).view(-1, 1).to(device), 0) # scatter:散射张量 对角线为0，其余为1

        ## it produces 1 for the non-matching places and 0 for matching places i.e its opposite of mask
        mask = mask * logits_mask
        # compute log_prob with logsumexp
        logits_max, _ = torch.max(anchor_dot_contrast, dim=1, keepdim=True)
        logits = anchor_dot_contrast - logits_max.detach()
        exp_logits = torch.exp(logits) * logits_mask
        # exp_logits = torch.exp(logits) * logits_mask * unmask

        ## log_prob = x - max(x1,..,xn) - logsumexp(x1,..,xn) the equation
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True))

        # compute mean of log-likelihood over positive
        mean_log_prob_pos = (mask * log_prob).sum(1) / mask.sum(1)
        # loss
        loss = -1 * mean_log_prob_pos
        loss = loss.mean()

        return loss

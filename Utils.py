from IPython.core.display import display, HTML
import re

import numpy as np
import matplotlib.pyplot as plt

import matplotlib.gridspec as gridspec
from sklearn.metrics import classification_report

def set_square_aspect(axes) :
    x0,x1 = axes.get_xlim()
    y0,y1 = axes.get_ylim()
    axes.set_aspect(abs(x1-x0)/abs(y1-y0))

#################### Preprocessing Begin ############################################

def sortbylength(X, y) :
    len_t = np.argsort([len(x) for x in X])
    X1 = [X[i] for i in len_t]
    y1 = [y[i] for i in len_t]
    return X1, y1

def add_frequencies(vec, X) :
    freq = np.zeros((vec.vocab_size, ))
    for x in X :
        for w in x :
            freq[w] += 1
    freq = freq / np.sum(freq)
    vec.freq = freq

def exec_jupyter() :
    HTML("""
    <style>
    .jp-Stdin-input {
        width: 80% !important;
        height : 1.5em !important;
        font-size : 1em;
        background : white;
        border:1px solid #cccccc;
    }
    </style>
    """)
    
def filterbylength(X, y, min_length = None, max_length = None) :
    lens = [len(x)-2 for x in X]
    min_l = min(lens) if min_length is None else min_length
    max_l = max(lens) if max_length is None else max_length

    idx = [i for i in range(len(X)) if len(X[i]) > min_l+2 and len(X[i]) < max_l+2]
    X = [X[i] for i in idx]
    y = [y[i] for i in idx]

    return X, y


def evaluate_and_print(model, X, y) :
    yhat, attn = model.evaluate(X)
    yhat = np.array(yhat)[:, 0]
    rep = classification_report(y, (yhat > 0.5))
    print(rep)

    return yhat, attn

#################################### Preprocessing End ########################################################

def calc_entropy(X, attn) :
    H = []
    for i in range(len(X)) :
        h = attn[i][:len(X[i])]
        a = h * np.log(np.clip(h, a_min=1e-8, a_max=None))
        a = -a.sum()
        H.append(a)

    return H

def get_entropy(X, attn) :
    unif_H, attn_H = [], []
    for i in range(len(X)) :
        h = attn[i][:len(X[i])]
        a = h * np.log(np.clip(h, a_min=1e-8, a_max=None))
        a = -a.sum()
        unif_H.append(np.log(len(X[i])))
        attn_H.append(a)

    return unif_H, attn_H

def plot_entropy(X, attn) :
    unif_H, attn_H = [], []
    for i in range(len(X)) :
        h = attn[i][:len(X[i])]
        a = h * np.log(np.clip(h, a_min=1e-8, a_max=None))
        a = -a.sum()
        unif_H.append(np.log(len(X[i])))
        attn_H.append(a)

    plt.scatter(attn_H, unif_H, s=1)

##################################################################################################################

def print_attn(sentence, attention, idx=None) :
    l = []
    for i, (w, a) in enumerate(zip(sentence, attention)) :
        w = re.sub('&', '&amp;', w)
        w = re.sub('<', '&lt;', w)
        w = re.sub('>', '&gt;', w)
        
        add_string = ''
        if idx is not None and i == idx :
            add_string = "border-style : solid;"
        
        l.append('<span style="background-color:hsl(360,100%,' + str((1-a) * 50 + 50) + '%);' + add_string + '">' + w + ' </span>')
    
    display(HTML(''.join(l)))

def plot_diff(sentence_1, idx, new_word, old_attn, new_attn) :
    # need vec in environment
    L = len(sentence_1)
    print_attn(sentence_1, old_attn[:L], idx)
    sentence_1 = [x for x in sentence_1]
    sentence_1[idx] = new_word
    print("-"*20)
    print_attn(sentence_1, new_attn[:L], idx)

#######################################################################################################################

def process_grads(grads) :
    for k in grads :
        xxe = grads[k]
        for i in range(len(xxe)) :
            xxe[i] = np.abs(xxe[i])
            xxe[i] = xxe[i] / xxe[i].sum()

def plot_grads(X, attn, grads) :
    fig = plt.figure(figsize=(15, 15))
    gs = gridspec.GridSpec(3, 3, figure=fig)
    ax = []
    for i in range(len(grads)) :
        ax.append(plt.subplot(gs[i//3, i%3]))

    colnum = 0
    for k in grads :
        xxe = grads[k]    
        a, x = [], []
        for i in range(len(xxe)) :
            a += list(attn[i][:len(X[i])])
            x += list(xxe[i][:len(X[i])])
            
        coef = np.corrcoef(a, x)[0, 1]
        axes = ax[colnum]
        colnum += 1

        axes.hexbin(a, x, mincnt=1, gridsize=50, cmap='PiYG', extent=(0, 1, 0, 1))
        axes.set_ylim(0, 1)
        axes.set_xlim(0, 1)
        axes.set_title(k + ' rho=' + str(coef))
        set_square_aspect(axes)

    plt.tight_layout()
    plt.show()

##########################################################################################################################

def generate_medians_from_sampling_top(output, attn, yhat) :
    perts_attn, words_sampled, best_attn_idxs, perts_output = output

    n_top = perts_attn[0].shape[2]
    perts_attn_med = [np.median(perts_attn[i], 1) for i in range(len(perts_attn))]
    perts_output_sum = [x.mean(0) for x in perts_output]

    meds, attn_meds, out_sum = [], [], []
    for i in range(len(perts_attn)) :
        m = perts_attn_med[i]
        for j in range(n_top) :
            meds.append(m[best_attn_idxs[i][j], j])
            attn_meds.append(attn[i][best_attn_idxs[i][j]])
            out_sum.append(perts_output_sum[i][j] - yhat[i])

    plt.scatter(attn_meds, meds, s=1)
    plt.show()

    plt.scatter(attn_meds, out_sum, s=1)
    plt.show()

def get_distractors(sampled_output, attn_hat) :
    perts_attn, words_sampled, best_attn_idxs = sampled_output
    perts_attn_med = [np.median(perts_attn[i], 1) for i in range(len(perts_attn))]
    
    n_top = perts_attn[0].shape[2]
    median_attention = []
    for i in range(len(perts_attn_med)) :
        med = perts_attn_med[i]
        med_at_idx = []
        for j in range(n_top) :
            med_at_idx.append(med[best_attn_idxs[i][j], j])

        median_attention.append(med_at_idx)
        
    num_high_med_high_attn = 0
    num_high_attn = 0
    
    distractors = []
    for i, x in enumerate(best_attn_idxs) :
        idxs = best_attn_idxs[i]
        for j, idx in enumerate(idxs) :
            if attn_hat[i][idx] > 0.5 : 
                num_high_attn += 1
                if median_attention[i][j] > 0.5 :
                    num_high_med_high_attn += 1
                    distractors.append((i, j, idx))
                    
    print(num_high_med_high_attn / num_high_attn * 100, num_high_med_high_attn, num_high_attn)
    return distractors

def print_few_distractors(vec, X, attn_hat, sampled_output, distractors) :
    perts_attn, words_sampled, best_attn_idxs = sampled_output

    for (i, j, idx) in distractors :
        sentence = vec.map2words(X[i])
        attn = attn_hat[i][:len(sentence)]
        pos = j
        w = np.argsort(perts_attn[i][idx, :, j])[len(perts_attn[i][idx, :, j])//2]

        new_word = vec.idx2word[int(words_sampled[i][w])]

        plot_diff(sentence, idx, new_word, attn, perts_attn[i][:, w, pos])
        print("*"*40)

###########################################################################################################################

def plot_permutations(permutations, X, yhat, attn) :
    perm_med = np.array([np.median(x) for x in permutations])
    max_attn = [max(attn[i][:len(X[i])]) for i in range(len(attn))]

    fig = plt.figure(figsize=(15, 15))
    gs = gridspec.GridSpec(4, 4, figure=fig)
    ax = []
    for i in range(4) :
        ax.append(plt.subplot(gs[i//4, i%4]))

    ax[0].scatter(yhat, perm_med - yhat, s=1)
    ax[0].set_xlabel('$\\hat{y}$')
    ax[0].set_ylabel('$\\bigtriangleup \\hat{y}$')
    set_square_aspect(ax[0])

    col = np.where(yhat > 0.5, 'g', 'r')
    ax[1].scatter(max_attn, perm_med - yhat, s=1, c=col)
    ax[1].set_xlabel('Max attention')
    ax[1].set_ylabel('$\\bigtriangleup \\hat{y}$')
    set_square_aspect(ax[1])

    ue, ae = get_entropy(X, attn)

    ax[2].scatter(ae, perm_med - yhat, s=1, c=col)
    ax[2].set_xlabel('Attention Entropy')
    ax[2].set_ylabel('$\\bigtriangleup \\hat{y}$')
    set_square_aspect(ax[2])

    ax[3].scatter(ue, perm_med - yhat, s=1, c=col)
    ax[3].set_xlabel('Uniform Entropy')
    ax[3].set_ylabel('$\\bigtriangleup \\hat{y}$')
    set_square_aspect(ax[3])

    plt.subplots_adjust(wspace=0, hspace=0)
    plt.tight_layout()
    plt.show()

################################################################################################################################

def kld(a1, a2) :
    #(B, *, A), #(B, *, A)
    a1 = np.clip(a1, 0, 1)
    a2 = np.clip(a2, 0, 1)
    log_a1 = np.log(a1 + 1e-10)
    log_a2 = np.log(a2 + 1e-10)

    kld_v = a1 * (log_a1 - log_a2)
    kld_v = kld_v.sum(-1)

    return kld_v

def jsd(p, q) :
    m = 0.5 * (p + q)
    jsd_v = 0.5 * (kld(p, m) + kld(q, m))

    return jsd_v

def plot_adversarial(X, y_hat, attn, adversarial_outputs) :
    ad_y, ad_attn = adversarial_outputs
    ad_y = np.array(ad_y)[:, 0]

    fig = plt.figure(figsize=(15, 15))
    gs = gridspec.GridSpec(3, 3, figure=fig)
    ax = []
    for i in range(5) :
        ax.append(plt.subplot(gs[i//3, i%3]))

    ax[0].scatter(y_hat, ad_y, s=1)
    ax[0].set_xlabel("True Output")
    ax[0].set_ylabel("Adversarial Output")
    ax[0].set_title("True vs Adversarial Output")
    set_square_aspect(ax[0])

    jds = [jsd(attn[i][:len(X[i])], ad_attn[i][:len(X[i])]) for i in range(len(X))]
    p30 = len(np.where(np.array(jds) > 0.3)[0]) / len(attn)
    ax[1].hist(jds, bins=20)
    ax[1].set_title("Histogram of JS Divergence : p30 = " + str(p30))
    set_square_aspect(ax[1])

    pos_neg_col = np.where(np.array(y_hat) > 0.5, 'g', 'r')
    ax[2].scatter(jds, np.abs(np.array(np.array(y_hat) - np.array(ad_y))), s=1, c=pos_neg_col)
    ax[2].set_xlabel("JS Divergence")
    ax[2].set_ylabel("$\\bigtriangleup y$")
    ax[2].set_title("JS Divergence vs $\\bigtriangleup y$")
    set_square_aspect(ax[2])

    ue, ae = get_entropy(X, attn)
    ax[3].scatter(ae, jds, s=1, c=pos_neg_col)
    ax[3].set_xlabel("Attention Entropy")
    ax[3].set_ylabel("JS DIvergence")
    ax[3].set_title("JS Divergence vs Attention Entropy")
    set_square_aspect(ax[3])

    orig_H, opt_H = calc_entropy(X, attn), calc_entropy(X, ad_attn)
    ax[4].scatter(orig_H, opt_H, s=1, c=pos_neg_col)
    lim = max(max(orig_H), max(opt_H))
    ax[4].set_xlim(0, lim)
    ax[4].set_ylim(0, lim)
    ax[4].set_xlabel("Original Attention Entropy")
    ax[4].set_ylabel("Adversarial Attention Entropy")
    ax[4].set_title("Change in Entropies")
    set_square_aspect(ax[4])

    plt.subplots_adjust(wspace=0, hspace=0)
    plt.tight_layout()
    plt.show()

    return jds

def print_adversarial_example(sentence, attn, attn_new) :
    L = len(sentence)
    print_attn(sentence, attn[:L])
    print('-'*20)
    print_attn(sentence, attn_new[:L])

############################################################################################################

def jsd_bern(p, q) :
    return jsd(np.array([1-p, p]), np.array([1-q, q]))

def plot_y_diff(X, attn, yhat, ynew_list, usehexbin=False) :
    y_diff = [ynew_list[i] - yhat[i] for i in range(len(yhat))]
    
    a = []
    b = []
    for i in range(len(attn)) :
        L = len(X[i])
        a += list(attn[i][:L])
        f = np.abs(y_diff[i][:L])
        f = f / f.sum()
        b += list(f) #y_diff[i][:L])

    if usehexbin :
        plt.hexbin(a, b, mincnt=1, gridsize=50, cmap='PiYG')
    else :
        plt.scatter(a, b, s=1)

    plt.xlabel("Attention")
    plt.ylabel("$\\bigtriangleup y$")
    plt.title("Attention vs change in output")
    plt.show()

def plot_attn_diff(X, attn, attn_new, title=None, usehexbin=False) :
    a = []
    b = []
    for i in range(len(attn)) :
        L = len(X[i])
        a += list(attn[i][:L])
        b += list(attn_new[i][:L])

    if usehexbin :
        plt.hexbin(a, b, mincnt=1, gridsize=50, cmap='PiYG')
    else :
        plt.scatter(a, b, s=1)

    plt.xlabel("Old Attention")
    plt.ylabel("New Attention")
    plt.title("Old vs New Attention" if title is None else title)
    plt.show()
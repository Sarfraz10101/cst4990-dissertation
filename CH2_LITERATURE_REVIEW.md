# Chapter 2: Literature Review

*Final. Matches the submitted dissertation (`CST4990_Dissertation_Masood_final.docx`).
Every citation below is checked against DBLP (or, for arXiv/NIST material, the
publisher's own record), see `REFERENCES.md` for the verification note on each.*

## 2.1 Physical side-channel analysis

Kocher, Jaffe and Jun (1999) established that a cryptographic implementation's
instantaneous power consumption is statistically correlated with the secret data
it processes, and that this correlation survives averaging across many
measurements even in the presence of substantial measurement noise: differential
power analysis (DPA). The result reframed physical side channels from a
theoretical curiosity into a practical attack against otherwise mathematically
secure algorithms: security had to be evaluated at the level of the physical
implementation, not only the algorithm. Genkin et al. (2015, 2016) later showed
that the same class of leakage is exploitable on unmodified, commodity personal
computers using low-cost equipment: electromagnetic and even acoustic emanations
from a laptop are sufficient to recover a private key during decryption, with no
physical modification of the target required. Read together, these two results
establish the pattern this dissertation extends one abstraction layer up: a
side channel need not require specialised measurement equipment or a purpose-built
target, only a resource whose consumption both correlates with secret state and is
observable by an adversary. For this dissertation's design, the implication is
methodological rather than mechanistic: if commodity hardware and off-the-shelf
sensors are sufficient to mount a DPA-class attack, then the absence of
specialised equipment in this project's own setup (Section 3.3) is not a reason to treat
the resulting channel as a weaker or less realistic threat; it is consistent
with where the field's own attacks have moved.

## 2.2 Noise and masking countermeasures

Chari et al. (1999) provide the theoretical foundation for evaluating noise as a
countermeasure. They model an attacker who must average over many measurements to
overcome noise, and show formally that the number of measurements required grows
with the square of the added noise's standard deviation: noise raises the
*cost* of an attack rather than removing the underlying correlation between
secret state and physical signal. This is the central prediction this
dissertation tests directly, translated from a cryptographic hardware setting to
a kernel packet filter: if noise injection behaves as Chari et al. predict, an
attacker's accuracy should recover as their observation budget grows, rather than
remaining permanently suppressed. Mangard (2004) operationalises the same
question empirically, developing a statistical method to calculate exactly how
many additional traces a given hardware countermeasure forces an attacker to
collect, and demonstrating that this "trace-multiplication" framing allows
different countermeasures to be compared on a single, principled metric rather
than a single accuracy figure collected at one arbitrary sample size. That
framing is the direct methodological ancestor of the observation-budget sweep
this dissertation uses in Chapter 4: reporting a factor and a curve, not a
solitary accuracy number, is the established way to evaluate a noise-based
defence properly, and its comparative absence from applied, non-cryptographic
noise-injection evaluations is part of the gap this dissertation addresses.
Masure, Dumas and Prouff (2020) extend this line of evaluation into the
deep-learning era, building an information-theoretic framework connecting
modern neural-network attack metrics back to the classical guessing-entropy and
mutual-information measures Chari and Mangard's generation used, and applying it
directly to how masking and desynchronisation countermeasures degrade a
deep-learning attacker's efficiency, confirming that the trace-multiplication
question this dissertation asks of a kernel firewall is still an open,
actively-studied one against contemporary machine-learning adversaries, not a
question the field considers settled from 1999 to 2004.
Neither the classical nor the deep-learning literature considers a defence whose noise is purely additive with respect to
the measured quantity, as distinct from noise that can shift a signal in either
direction around its true value. That distinction matters here: an
additive-only defence can inflate an observed latency but can never make it
smaller than the underlying, noise-free minimum, so it cannot touch the lower
tail of a latency distribution however much noise is added. Chapter 4's central
finding, that this project's defence leaves an attacker trained on lower-tail
statistics almost entirely unaffected, is best read as a previously unstated
consequence of the noise being additive rather than symmetric, a case Chari et
al.'s general argument permits but does not itself distinguish from the
symmetric case.

## 2.3 Side channels in virtualised co-tenancy

Ristenpart et al. (2009) demonstrated that virtual machines belonging to
different, mutually distrusting tenants, when co-located on the same physical
cloud host, can leak information to each other purely through shared hardware
resource contention, with neither party's cooperation and without either
crossing the hypervisor's isolation boundary in the conventional sense. This
established co-tenancy itself, rather than any particular software
vulnerability, as a side channel, and is the direct ancestor of the threat model
in this dissertation: an unprivileged, merely co-located observer. Zhang et al.
(2011) extended this line of work by inverting it defensively: using the same
class of cache-based side channel that an attacker would use to *detect*
unwanted co-residency, so that a tenant can tell whether a competing VM shares
its host. Their result is evidence, from the defender's side, of exactly how much
information a resource-contention channel carries in a virtualised environment,
and supports treating a hypervisor-hosted setting (as used throughout this
dissertation's own experimental design, Section 3.3) as a realistic environment for this
class of leak rather than a laboratory contrivance. Both papers, however,
concern channels arising from contention for a *shared* hardware resource
(last-level cache) between processes that a scheduler may or may not place on
the same physical core at any given moment. This dissertation's channel is
narrower and, in one respect, more direct: it does not depend on the attacker
sharing a cache with the victim at all, only on being able to send traffic the
victim's kernel will process, so co-residency in Ristenpart et al.'s sense is
sufficient but not necessary for the leak studied here. The trade-off is that
the effectiveness of the *defence*, unlike the leak itself, turns out to depend
on exactly the kind of shared-resource contention Zhang et al. exploit
defensively: Section 3.7 and Section 4.5 show that the noise injector must be placed on the
victim's own core to have any measurable effect, which is a same-core, not
cross-core, contention requirement.

## 2.4 Machine learning as the attacker model

A side channel is only a practical concern if a realistic adversary can exploit
it without hand-crafted, target-specific signal processing. Hettwer, Gehrer and
Güneysu (2020) survey the substantial and still-growing body of work applying
machine learning, from classical models to deep neural networks, directly to
raw or lightly processed side-channel traces, and show that learned classifiers
can match or exceed hand-engineered attacks such as template attacks across a
range of targets, while requiring markedly less domain expertise from the
attacker to construct. This supports the choice, in this dissertation's own
design (Section 3.8), of a generic classifier (logistic regression and random forest,
neither designed with any prior knowledge of the specific leak mechanism) as a
credible stand-in for a realistic adversary, rather than requiring a bespoke,
hand-tuned attack to demonstrate that the leak is exploitable. The survey also
identifies a recurring evaluation pitfall directly relevant to this
dissertation's own controls (Section 3.7): reported accuracy figures are frequently
inflated by information leakage between training and test data, particularly
where correlated samples (from the same trace, device, or session) are split
across the training/test boundary rather than grouped, the same failure mode
this dissertation's grouped cross-validation is designed to prevent.

## 2.5 Kernel packet filtering and ACL cost

The framing claim that packet-filtering configuration is worth protecting rests
on two premises: that access-control enforcement is now distributed throughout a
network rather than concentrated at its perimeter, and that the cost of
evaluating a filtering rule set is not uniform, so its structure is in principle
observable. NIST Special Publication 800-207 (Rose et al., 2020) formalises the
first premise as the zero-trust architecture model, in which every access
request is evaluated against policy at the point of use rather than trusted by
virtue of network location: meaning a policy enforcement point, such as the
kernel firewall studied here, exists at many places in a modern network, and its
configuration is a target of independent value at each one. Niemann, Pfingst and
Göbel (2015) support the second premise directly, empirically measuring Linux's
netfilter subsystem and showing that packet-processing throughput degrades
measurably as the number of rules in a chain grows, because netfilter (and its
successor, `nftables`, used throughout this dissertation) evaluates rules
sequentially rather than in a structure with sub-linear lookup cost. This is
the mechanism the experimental harness in Chapter 3 exploits directly: chain
depth is not merely logically distinguishable but measurably more expensive to
evaluate, which is what makes it observable through a timing channel at all.

## 2.6 Research gap

Noise injection as a side-channel countermeasure is well studied in the
cryptographic-hardware literature (Section 2.2), and co-tenancy side channels are well
studied at the level of cache and memory-bus contention (Section 2.3). What is thin is
the intersection: noise injection evaluated against a *kernel policy-enforcement*
mechanism rather than a cryptographic primitive, using a *realistic
machine-learning* adversary rather than a hand-derived statistical distinguisher,
and evaluated against an *observation budget* rather than a single accuracy
figure at one arbitrarily-chosen sample size. Mangard's (2004) trace-
multiplication framing, and its modern deep-learning-era counterpart in Masure,
Dumas and Prouff (2020), exist in the cryptographic hardware literature but are
not standard practice in applied, systems-level noise-injection evaluations,
where a single accuracy number before and after the defence is more commonly
reported. This dissertation addresses that gap directly: it evaluates an
algorithmic noise-injection defence against a kernel firewall configuration
leak, with a machine-learning attacker, reporting both a single-shot accuracy
comparison and a full observation-budget curve, so that the difference between a
defence that eliminates a leak and one that merely rate-limits its observation,
the distinction Chari et al. (1999) predict theoretically, can be seen directly
in the results rather than assumed from the headline number alone.

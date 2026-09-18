# Verified references

Every entry below was checked against DBLP on **21 August 2026**. The
verification status is recorded per entry: do not silently promote anything to
"verified" without actually checking it.

Middlesex Harvard style, matching the format already used in the proposal.

---

## Removed: fabricated

> ~~Genkin, D., Pachmanov, L., Pipman, I. and Tromer, E. (2014) 'EPIC: Efficient
> Power-Analysis Attacks on Cryptographic Implementations', *Journal of
> Cryptographic Engineering*, 4(2), pp. 89–103.~~

**This paper does not exist.** Evidence:

1. *JCEN* 4(2) (June 2014) contains exactly five articles: Almeida et al.
   (75–89), Nègre (91–106), Carlet et al. (107–121), Biasi et al. (123–134),
   Paul & Chattopadhyay (135–143). No "EPIC", no Genkin.
2. The cited span pp. 89–103 is not a valid article range in that issue: one
   article ends at 89, the next begins at 91.
3. The four named authors' earliest *joint* publication of any kind is 2015.

Delete it from the proposal and from anything downstream. Then check every
other reference in your draft the same way; a fabricated citation usually
arrives with siblings.

## Correction to an existing reference

The Kocher entry cites "Proceedings of the 24th annual international cryptology
conference". CRYPTO '99 was the **19th** Annual International Cryptology
Conference (the series began in 1981; the 24th was 2004). Fix the ordinal.

---

## Verified: use these

**Foundational power analysis** *(corroborated: DBLP lists this record, and its
page range 388–397 sits immediately before Chari et al. at 398–412 in the same
proceedings, which cross-checks both)*

> Kocher, P., Jaffe, J. and Jun, B. (1999) 'Differential power analysis', in
> Wiener, M. (ed.) *Advances in Cryptology — CRYPTO '99, 19th Annual
> International Cryptology Conference*. Lecture Notes in Computer Science 1666.
> Berlin: Springer, pp. 388–397.

**The countermeasure your project actually implements**: noise and masking as a
defence against power analysis. This is the correct ancestor for
"algorithmic noise injection", and it is the citation the fabricated one should
have been. *(Directly verified, DBLP.)*

> Chari, S., Jutla, C.S., Rao, J.R. and Rohatgi, P. (1999) 'Towards sound
> approaches to counteract power-analysis attacks', in Wiener, M. (ed.)
> *Advances in Cryptology — CRYPTO '99*. Lecture Notes in Computer Science 1666.
> Berlin: Springer, pp. 398–412.

**Your threat model**: cross-VM information leakage between co-located tenants.
Your proposal's phrase "from co-located virtual instances" is describing exactly
this paper's setting, so it belongs in the introduction. *(Directly verified,
DBLP: key `conf/ccs/RistenpartTSS09`.)*

> Ristenpart, T., Tromer, E., Shacham, H. and Savage, S. (2009) 'Hey, you, get
> off of my cloud: exploring information leakage in third-party compute clouds',
> in *Proceedings of the 16th ACM Conference on Computer and Communications
> Security (CCS '09)*. New York: ACM, pp. 199–212.
> doi: 10.1145/1653662.1653687.

**Physical side channels on commodity PCs**: what the Genkin group actually
published, and a legitimate substitute for the fabricated entry. *(Verified via
DBLP author search.)*

> Genkin, D., Pachmanov, L., Pipman, I. and Tromer, E. (2015) 'Stealing keys
> from PCs using a radio: cheap electromagnetic attacks on windowed
> exponentiation', in *Cryptographic Hardware and Embedded Systems (CHES 2015)*.
> Lecture Notes in Computer Science. Berlin: Springer, pp. 207–228.

**Accessible journal overview of the same work**: useful for the literature
review because it is a survey-style treatment in a mainstream venue.
*(Verified via DBLP author search.)*

> Genkin, D., Pachmanov, L., Pipman, I., Shamir, A. and Tromer, E. (2016)
> 'Physical key extraction attacks on PCs', *Communications of the ACM*, 59(6),
> pp. 70–79.

---

## Gaps filled, verified 28 August 2026

Same standard as above: checked against DBLP by exact title, or against the
publisher's own record where DBLP does not index the venue (arXiv preprints,
NIST special publications).

**ML-based side-channel analysis**: supports the claim that a classifier is a
credible attacker model; Section 2.4. *(Directly verified, DBLP key
`journals/jce/HettwerGG20`.)*

> Hettwer, B., Gehrer, S. and Güneysu, T. (2020) 'Applications of machine
> learning techniques in side-channel attacks: a survey', *Journal of
> Cryptographic Engineering*, 10(2), pp. 135–162. doi: 10.1007/s13389-019-00212-8.

**Cache/timing channels in cloud co-tenancy**: post-2009 development of the
Ristenpart et al. threat model, using a side channel defensively; Section 2.3.
*(Directly verified, DBLP key `conf/sp/ZhangJOR11`.)*

> Zhang, Y., Juels, A., Oprea, A. and Reiter, M.K. (2011) 'HomeAlone:
> co-residency detection in the cloud via side-channel analysis', in *2011 IEEE
> Symposium on Security and Privacy*. Los Alamitos, CA: IEEE, pp. 313–328.
> doi: 10.1109/SP.2011.31.

**Netfilter/nftables performance characterisation**: supports the claim that
chain traversal cost is depth-dependent; Section 2.5. Not indexed on DBLP (DBLP does
not index arXiv preprints), but the record is directly verifiable at
`arxiv.org/abs/1502.05487`; cite as a preprint, not as peer-reviewed.

> Niemann, R., Pfingst, U. and Göbel, R. (2015) *Performance evaluation of
> netfilter: a study on the performance loss when using netfilter as a
> firewall*. arXiv:1502.05487 [cs.NI].

**Noise-injection countermeasure evaluations**: prior art quantifying how much
a noise-based countermeasure actually raises attacker cost, the direct
statistical ancestor of this project's trace-multiplication measurement; Section 2.2.
*(Directly verified, DBLP key `conf/ctrsa/Mangard04`.)*

> Mangard, S. (2004) 'Hardware countermeasures against DPA — a statistical
> analysis of their effectiveness', in Okamoto, T. (ed.) *Topics in Cryptology
> — CT-RSA 2004*. Lecture Notes in Computer Science 2964. Berlin: Springer,
> pp. 222–235.

**Zero-trust architecture and ACL enforcement**: the framing claim in the
opening paragraph of Chapter 1 and Section 2.5. Not a DBLP-indexed academic paper; it
is the standards document itself, verifiable at `doi.org/10.6028/NIST.SP.800-207`.

> Rose, S., Borchert, O., Mitchell, S. and Connelly, S. (2020) *Zero trust
> architecture*. NIST Special Publication 800-207. Gaithersburg, MD: National
> Institute of Standards and Technology. doi: 10.6028/NIST.SP.800-207.

---

## Added following supervisor review, verified 16 September 2026

David Neilson's comments on the reviewed draft flagged Chari (1999) and Mangard
(2004) as extremely old sources for the noise-countermeasure discussion, and
asked for a citation supporting the cross-validation-leakage claim in Section 3.7. Both
gaps filled with DBLP-verified sources.

**Modern (deep-learning-era) noise/masking countermeasure evaluation**: pairs
with Chari (1999) and Mangard (2004) in Section 2.2/Section 2.6, and with the Chari citation
in Section 6.1, to show the trace-multiplication question is still actively studied
against contemporary ML attackers, not settled as of 1999–2004. *(Directly
verified, DBLP key `journals/iacr/MasureDP19`, published in TCHES 2020(1).)*

> Masure, L., Dumas, C. and Prouff, E. (2020) 'A comprehensive study of deep
> learning for side-channel analysis', *IACR Transactions on Cryptographic
> Hardware and Embedded Systems*, 2020(1), pp. 348–375.
> doi: 10.13154/tches.v2020.i1.348-375.

**Cross-validation leakage inflating side-channel/microarchitectural ML
accuracy**: supports the claim in Section 3.7 that splitting correlated samples
across the train/test boundary is the most common way published classifiers
in this space overstate their accuracy. *(Directly verified, DBLP key
`conf/ccs/ZhouGJEJ18`.)*

> Zhou, B., Gupta, A., Jahanshahi, R., Egele, M. and Joshi, A. (2018) 'Hardware
> performance counters can detect malware: myth or fact?', in *Proceedings of
> the 2018 ACM Asia Conference on Computer and Communications Security
> (ASIACCS '18)*. New York: ACM, pp. 457–468. doi: 10.1145/3196494.3196515.

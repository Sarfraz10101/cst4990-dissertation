# Chapter 1: Introduction

*Final. Matches the submitted dissertation (`CST4990_Dissertation_Masood_final.docx`).*

## 1.1 Background and motivation

Modern zero-trust network architectures assume that no host or path is trusted by
default, and enforce that assumption largely through kernel-level packet filtering:
Linux's `nftables` (and its predecessor, `iptables`) sits in the data path of every
packet a host sends or receives, evaluating an access control list before deciding
whether traffic proceeds. NIST's reference model for this design (Rose et al.,
2020) formalises access control as a decision made at the point of use: a policy
enforcement point evaluates every request against current policy, rather than
inheriting trust from network location. That means enforcement, and therefore
the configuration governing it, is distributed across many hosts rather than
concentrated at a single perimeter gateway. The specific configuration of any one
of those filters (which ports are open, which hosts are trusted, how deep the
rule chain is) is itself sensitive information. Knowing a target's firewall
configuration lets an attacker choose which services to probe, which ports are
silently dropped rather than actively refused, and how a security policy is
structured, all without triggering an alert that a direct configuration query
would. Because zero-trust designs place enforcement points throughout the network
rather than only at its perimeter, the configuration of any one of those points is
worth protecting even though it never itself changes the response an attacker's
own connection receives. Unlike a perimeter firewall, a policy enforcement
point close to a workload is plausibly co-located with exactly the kind of
untrusted, multi-tenant process this dissertation's threat model assumes.

## 1.2 Problem definition

A firewall configuration can leak through channels other than its intended
responses. On the loopback path, the Linux kernel evaluates the `nftables` `INPUT`
hook synchronously, inside the calling process's own execution context, so the
observable latency of a single `sendto()` call is a function of how many rules the
kernel evaluated and which verdict it reached. An unprivileged, co-located observer
(one able to run code or exchange traffic with the host, but without filesystem or
management-plane access) can therefore recover firewall state purely from resource-
consumption signals: execution time and CPU footprint. This is the same class of
threat identified for cross-tenant cloud environments by Ristenpart et al. (2009),
who showed that co-located virtual instances can extract information about each
other purely through resource contention, without either party's cooperation or
knowledge. The leak is measurable in the first place because rule evaluation cost
is not constant: Niemann, Pfingst and Göbel (2015) show empirically that Linux's
netfilter subsystem processes packets more slowly as the number of rules in a
chain grows, since rules are evaluated sequentially rather than through a
structure with sub-linear lookup cost. A realistic adversary does not need to
hand-derive the relationship between rule depth and latency either; Hettwer,
Gehrer and Güneysu (2020) survey a substantial body of work showing that a
generic, off-the-shelf classifier can learn to exploit a physical or resource
side channel directly from raw measurements, without the attacker possessing
prior knowledge of the underlying mechanism. This dissertation treats kernel
packet-filtering configuration as the specific secret at risk, adopts a generic
classifier as its attacker model on that basis, and asks whether a lightweight,
software-only defence can protect the configuration against it.

## 1.3 Aim and objectives

The aim of this project is to evaluate whether algorithmic noise injection is an
effective and practical defence against resource-consumption side-channel analysis
of kernel firewall configuration. The three objectives are:

1. To build an experimental harness capable of measuring, with statistical rigour,
   whether a machine-learning attacker can recover firewall configuration from
   timing and resource-utilisation signals alone.
2. To implement and evaluate an algorithmic noise-injection defence against that
   attacker, across multiple triggering strategies and injector placements.
3. To quantify the trade-off the defence imposes, in both attacker accuracy and
   computational overhead, at a level of detail sufficient to support a genuine
   deployment recommendation rather than a single pass/fail verdict.

## 1.4 Research questions

**RQ1.** To what extent does algorithmic noise injection reduce a machine-learning
attacker's accuracy in classifying firewall configuration from resource-
consumption signals, relative to a 25% chance baseline (four balanced
configuration classes)?

**RQ2.** What computational overhead, in CPU consumption and in latency imposed
on legitimate traffic, does the defence require to achieve that reduction?

## 1.5 Scope and limitations

This dissertation is scoped to a **timing and resource-utilisation side channel**,
not an electrical-power side channel. The proposal's title
references power-noise injection and cites differential power analysis (Kocher et
al., 1999) as its origin; the intended software proxy for electrical power draw,
Intel's RAPL energy counters, is masked inside VirtualBox and VMware guests and was
confirmed unreadable on the experimental platform by an automated preflight check
before every collection run. What is measured instead is execution-time and
CPU-utilisation footprint: the same broad category of physical side channel, one
abstraction layer removed from a true power trace. All findings in this
dissertation should be read as applying to that channel. Genuine power-domain
replication would require a native (non-virtualised) install with working RAPL
access, or dedicated power-measurement hardware, and is identified as further work
in Chapter 6.

## 1.6 Dissertation structure

Chapter 2 reviews prior work on power and physical side channels, noise-based
countermeasures, side channels in virtualised co-tenancy, and machine-learning
attacker models, before identifying the gap this project addresses. Chapter 3
describes the experimental harness, threat model, and the controls used to ensure
the results reflect a genuine side channel rather than a measurement artefact.
Chapter 4 presents the results without interpretation. Chapter 5 interprets those
results against the research questions and prior theory, states the study's
limitations, and makes deployment recommendations. Chapter 6 concludes and
identifies further work.

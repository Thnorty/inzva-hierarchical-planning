"""Build presentation/showcase.html from presentation/index.html.

The inzva showcase decks follow a house structure: agenda, meet the team,
problem statement, literature review, dataset, pipeline, methods, results,
demo, future directions, thank you. Our deck told the same story without six of
those sections, which is fine when we narrate it and a gap when the deck is
read next to the others.

This adds the six as new slides and splices them into the running order, rather
than rewriting the deck, so the eleven slides that were already reviewed keep
their exact wording. Run it again after any edit to index.html:

    python presentation/make_showcase.py presentation/index.html         presentation/showcase.html

Every number on a new slide comes from a record; presentation/README.md maps
each one to the file it lives in.
"""

import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])

html = SRC.read_text(encoding='utf-8')

# ---------------------------------------------------------------- extra CSS

CSS = """
/* Showcase deck: the house structure's six extra sections. */
.agenda{
  display:grid;grid-auto-flow:column;grid-template-rows:repeat(4,auto);
  gap:30px 72px;margin:52px 0 0;padding:0;list-style:none;max-width:1340px;
}
.agenda li{display:grid;grid-template-columns:58px 1fr;gap:20px;align-items:baseline;font-size:28px;line-height:1.3}
.agenda .nn{font-family:var(--mono);font-size:20px;color:var(--accent)}
.agenda small{display:block;font-size:19px;color:var(--ink-soft);margin-top:7px;line-height:1.4}

ul.lit{list-style:none;padding:0;margin:30px 0 0;display:grid;gap:15px;max-width:1340px}
.lit li{
  display:grid;grid-template-columns:230px 1fr 235px;gap:26px;align-items:baseline;
  border-top:1px solid var(--rule);padding-top:14px;font-size:20px;line-height:1.38;
}
.lit .w{font-size:25px;font-weight:600}
.lit .w small{
  display:block;font-family:var(--mono);font-size:14px;font-weight:400;margin-top:6px;
  color:var(--ink-soft);text-transform:uppercase;letter-spacing:.06em;
}
.lit .took{color:var(--ink-soft)}
.lit .got{font-family:var(--mono);font-size:18px;color:var(--accent);text-align:right;line-height:1.5}

.demo{display:grid;grid-template-columns:720px 430px;gap:56px;align-items:center;margin-top:26px;justify-content:space-between}

.part ul.todo{list-style:none;padding:0;margin:18px 0 0;display:grid;gap:16px}
.part ul.todo li{font-size:21px;line-height:1.4;padding-left:26px;position:relative}
.part ul.todo li::before{content:"\\2192";position:absolute;left:0;color:var(--accent);font-family:var(--mono)}
.part ul.todo b{font-weight:600;color:var(--ink)}
"""

html = html.replace('</style>', CSS + '</style>')
html = html.replace(
    '<title>Imagine, Then Push</title>',
    '<title>Imagine, Then Push — Showcase</title>',
)

# ------------------------------------------------------------- new slides

AGENDA = """<section class="slide" data-time="20">
  <p class="eyebrow">Agenda</p>
  <h2>Eight stops, and the two we care about are <em>6 and 7</em>.</h2>
  <ol class="agenda">
    <li><span class="nn">01</span><span>The team<small>Three of us, and who did what</small></span></li>
    <li><span class="nn">02</span><span>The task, and the problem<small>Pushing a T, and why reacting is not enough</small></span></li>
    <li><span class="nn">03</span><span>What we built on<small>The papers, the planner, the benchmark</small></span></li>
    <li><span class="nn">04</span><span>The data<small>18,685 expert demonstrations, no rewards</small></span></li>
    <li><span class="nn">05</span><span>Our method<small>Two world models at different time scales</small></span></li>
    <li><span class="nn">06</span><span>Results<small>Part 1: our planner. Part 2: a published one</small></span></li>
    <li><span class="nn">07</span><span>Demo<small>Six episodes, start to finish</small></span></li>
    <li><span class="nn">08</span><span>Where we go next<small>The result we still cannot explain</small></span></li>
  </ol>
  <div class="foot"><span class="src">Two parts, one lesson · about ten minutes</span><span class="pg"></span></div>
  <aside class="notes">Briefly: who we are, the task, what we built on, the data, our method, then the results, a demo, and what we would do next. The two results sections are the heart of it.</aside>
</section>"""

LITERATURE = """<section class="slide" data-time="35">
  <p class="eyebrow">What we built on</p>
  <h2>We changed <em>one thing</em>. The rest is borrowed, deliberately.</h2>
  <ul class="lit">
    <li>
      <span class="w">LeWM<small>latent world model</small></span>
      <span class="took">The recipe our own model copies, encoder and all. We planned with its released checkpoint first, to check our test bench before trusting it on our own.</span>
      <span class="got">published 96%<br>we measure 87.3%</span>
    </li>
    <li>
      <span class="w">Hi-LeWM<small>&ldquo;Mind the Gap&rdquo;, 2026</small></span>
      <span class="took">A published hierarchical planner that also picks waypoints before pushes. Part 2 takes it apart using the authors' own trained models.</span>
      <span class="got">its waypoints<br>cost it 22 points</span>
    </li>
    <li>
      <span class="w">DINO-WM<small>world model on frozen features</small></span>
      <span class="took">A second published reference, built on a frozen vision backbone instead of training its own — a check that our harness does not flatter one design.</span>
      <span class="got">84.0% here</span>
    </li>
    <li>
      <span class="w">CEM<small>the cross-entropy method</small></span>
      <span class="took">The planner itself, untouched: sample plans, keep the best tenth, resample around them. Our contribution changes <b>what it searches over</b>, never how it searches.</span>
      <span class="got">300 plans<br>30 rounds</span>
    </li>
    <li>
      <span class="w">Push-T<small>standard benchmark</small></span>
      <span class="took">The task, its demonstrations and its success criterion, all taken as given, so our numbers compare with anyone else's.</span>
      <span class="got">unmodified</span>
    </li>
  </ul>
  <div class="foot"><span class="src">All of it through the open-source stable-worldmodel library, at one pinned commit · INZVA_README.md §6, §11, §15</span><span class="pg"></span></div>
  <aside class="notes">We deliberately borrowed almost everything. The model recipe is LeWM's. The planner is the standard cross-entropy method, unchanged. The task and its data are the standard Push-T benchmark. Hi-LeWM is the published hierarchical planner that part two diagnoses, and DINO-WM is a second reference point. The only thing we changed is what the planner searches over.</aside>
</section>"""

DATASET = """<section class="slide" data-time="30">
  <p class="eyebrow">The data</p>
  <h2>18,685 expert demonstrations. <em>No rewards, no real robot.</em></h2>
  <div class="stats">
    <div class="stat">
      <div class="big">18,685</div>
      <p class="what">episodes</p>
      <p>Each an expert pushing the T into place, between <b>49 and 246</b> pushes long.</p>
    </div>
    <div class="stat">
      <div class="big">2.3<small>M</small></div>
      <p class="what">frames</p>
      <p>Each one a 224&times;224 picture, where the pusher is, and the push that was taken.</p>
    </div>
    <div class="stat">
      <div class="big">934</div>
      <p class="what">held back</p>
      <p>Split <b>by episode, never by frame</b>. Neighbouring frames are near-copies, so splitting those measures memory, not learning.</p>
    </div>
  </div>
  <p class="loopnote">The model only ever sees <b>pictures and pushes</b>. It is never told where the T really is, and never told during training whether a push was a good one. 43 GB on disk, and the same file the benchmark's own authors convert from.</p>
  <div class="foot"><span class="src">quentinll/lewm-pusht · verified by scripts/verify_dataset.py · split fingerprint 2d5f8c4f85e918f8 · INZVA_README.md §5</span><span class="pg"></span></div>
  <aside class="notes">The data is 18,685 expert episodes of this task, about 2.3 million frames. Crucially the model is never given the T's true position and never given a reward: it only sees pictures and the pushes that were made. We hold back 934 episodes, split at episode level, because consecutive frames in an episode are almost identical and a frame-level split would just measure memorisation.</aside>
</section>"""

METHODS = """<section class="slide" data-time="45">
  <p class="eyebrow">Our method · the model</p>
  <h2>A small model that predicts the <em>next 192 numbers</em>.</h2>
  <div style="margin-top:22px" id="fig-arch"></div>
  <div class="trio">
    <div>
      <div class="n ac">6.7M</div>
      <p>weights in total, most of them the encoder. Small enough to train the whole thing twice in a day on one desktop GPU.</p>
    </div>
    <div>
      <div class="n">7.5h</div>
      <p>to train the step-by-step model on an RTX A4000. The bigger-steps model reuses its frozen encoder and takes 2.5.</p>
    </div>
    <div>
      <div class="n">24&times;</div>
      <p>better at predicting the next scene than assuming nothing moves at all.</p>
    </div>
  </div>
  <div class="foot"><span class="src">stable_worldmodel/wm/gru/gru_wm.py · trained by scripts/train_gru.py · INZVA_README.md §10</span><span class="pg"></span></div>
  <aside class="notes">Here is the model. A small vision transformer turns the picture into 192 numbers. A GRU step takes those numbers and a push and predicts the next 192 numbers. That is the whole thing, under seven million weights. Two details matter. There is no decoder, so planning never generates pictures, only compares numbers. And the prediction depends only on the current numbers and the push, which is what lets a waypoint from the coarse model be handed to the fine one as a starting point.</aside>
</section>"""

DEMO = """<section class="slide" data-time="40">
  <p class="eyebrow">Demo</p>
  <h2>Six episodes, start to finish. <em>Nothing sped up.</em></h2>
  <div class="demo">
    <figure class="film" style="margin:0">
      <img src="assets/pusht-wall.gif" alt="Six test episodes running side by side, each pushing a blue-grey T-shaped block onto a pale green T that marks the goal pose." width="668" height="442">
      <figcaption>Six held-out test episodes from the Experiment A sweep, at real speed.</figcaption>
    </figure>
    <div class="side">
      <div>
        <div class="k">What you are seeing</div>
        <p>The blue dot is the pusher, the <b>pale green T</b> is where the block has to end up. The planner imagines ahead, makes ten pushes, looks again, then imagines from scratch.</p>
      </div>
      <div>
        <div class="k">Honestly</div>
        <p>These six were picked because they succeed. Across 250 episodes at this budget our planner succeeds <b>74%</b> of the time.</p>
      </div>
      <div><p class="dim">Recorded, not live: 600 samples, seed 4. A live run needs a GPU and about a minute an episode.</p></div>
    </div>
  </div>
  <div class="foot"><span class="src">assets/pusht-wall.gif, made by make_gifs.py from the sweep's own videos · notes/results/expA_sweep_results.md</span><span class="pg"></span></div>
  <aside class="notes">This is the planner actually running. Blue dot is the pusher, the pale green T is the goal pose. It plans ten pushes, executes them, looks at the real scene and replans. Being straight with you: these six are the successful episodes. At this budget it succeeds about 74 percent of the time over 250 episodes, which is the number on the earlier chart.</aside>
</section>"""

FUTURE = """<section class="slide" data-time="35">
  <p class="eyebrow">Where we go next</p>
  <h2>The result we <em>cannot explain</em> is the interesting one.</h2>
  <div class="parts">
    <div class="part">
      <span class="tag">Part 1 · our planner</span>
      <h3>Why did filling in the details add nothing?</h3>
      <ul class="todo">
        <li><b>Give the fine model a looser target.</b> We ask it to hit each waypoint exactly; following the coarse plan approximately may be what actually helps.</li>
        <li><b>Go deeper.</b> We tested two levels and jumps of two steps. Three levels, and bigger jumps, is the obvious next sweep.</li>
        <li><b>Beyond Push-T.</b> We dropped the planned test on the benchmark's other tasks for lack of compute, so we cannot yet claim this generalises.</li>
      </ul>
    </div>
    <div class="part">
      <span class="tag">Part 2 · the published planner</span>
      <h3>Three questions for its authors</h3>
      <ul class="todo">
        <li><b>How were the headline numbers produced?</b> With the library as released, that configuration cannot run at all.</li>
        <li><b>Why does the shipped setting differ</b> from the one the authors' own diagnostics use, when that one is 32 points better?</li>
        <li><b>Does the waypoint encoder memorise its training data?</b> There is no held-out split to check it against.</li>
      </ul>
    </div>
  </div>
  <p class="next"><b>The one we would run first:</b> in both parts the waypoints are the weak spot. Forcing them to look like scenes that can really happen, rather than sharpening them after the fact, is the experiment we would do next.</p>
  <div class="foot"><span class="src">INZVA_README.md §13 (what is still unmeasured), §14 · hilewm/docs/STATUS.md (open questions)</span><span class="pg"></span></div>
  <aside class="notes">Three directions. First, the thing we cannot explain: refinement added nothing. Our best guess is that we ask it to hit waypoints exactly when following them loosely is what matters. Second, we only tested two levels on one task; deeper hierarchies and other tasks are unmeasured. Third, part two leaves three open questions we would genuinely like to ask the paper's authors. And if we could run one experiment: constrain the waypoints to be scenes that can actually happen.</aside>
</section>"""

# ------------------------------------------- splice, in house-structure order

parts = re.split(r'\n<!-- (\d+) -->\n', html)
head = parts[0]
existing = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
if len(existing) != 11:
    sys.exit(f'expected 11 slides in {SRC}, found {len(existing)}')

# The tail (notes panel, controls, script) rides along with slide 11.
last, tail = existing[11].split('</section>', 1)
existing[11] = last + '</section>'

order = [
    existing[1],  # title + names
    AGENDA,
    existing[2],  # meet the team
    existing[3],  # the task = problem statement
    existing[4],  # why not a VLA
    LITERATURE,
    DATASET,
    existing[5],  # world models = the pipeline
    METHODS,
    existing[6],  # our idea: two time scales
    existing[7],  # results, part 1
    existing[8],  # results, part 2
    existing[9],  # results, part 2: why
    DEMO,
    existing[10],  # one lesson, found twice
    FUTURE,
    existing[11],  # sum up + thank you
]

body = ''.join(
    f'\n<!-- {i} -->\n{slide.strip()}\n' for i, slide in enumerate(order, 1)
)
html = head + body + tail

# ------------------------------------------------- the architecture figure

FIG = """  // The model, end to end. Only on the showcase deck's methods slide.
  (function(){
    if (!document.getElementById('fig-arch')) return;
    const s = svg('fig-arch', 1376, 300);
    const y = 46, bw = 110;
    frame(s, 0, y, bw, 'what it sees');
    T(s, bw / 2, y + bw / 2, 44, 25, C.soft);
    arrow(s, bw + 14, y + bw / 2, 204);

    el('rect', {x:214, y:y+5, width:210, height:100, rx:10, fill:C.wash, stroke:C.ac, 'stroke-width':2}, s);
    el('text', {x:319, y:y+46, 'font-size':25, 'text-anchor':'middle', fill:C.ink, style:serif}, s, 'ViT-tiny');
    el('text', {x:319, y:y+76, 'font-size':15, 'text-anchor':'middle', fill:C.soft}, s, '5.5M weights');
    arrow(s, 434, y + bw / 2, 524);

    function latent(x, label, hot){
      el('rect', {x, y:y+5, width:190, height:100, rx:10, fill:C.card,
                  stroke:hot ? C.ac : C.rule, 'stroke-width':hot ? 4 : 2}, s);
      el('text', {x:x+95, y:y+44, 'font-size':24, 'text-anchor':'middle',
                  fill:hot ? C.ac : C.ink, style:serif}, s, label);
      el('text', {x:x+95, y:y+74, 'font-size':15, 'text-anchor':'middle', fill:C.soft}, s, '192 numbers');
    }
    latent(534, 'the scene now', false);
    arrow(s, 734, y + bw / 2, 814);

    el('rect', {x:824, y:y+5, width:200, height:100, rx:10, fill:C.wash, stroke:C.ac, 'stroke-width':2}, s);
    el('text', {x:924, y:y+46, 'font-size':25, 'text-anchor':'middle', fill:C.ink, style:serif}, s, 'GRU step');
    el('text', {x:924, y:y+76, 'font-size':15, 'text-anchor':'middle', fill:C.soft}, s, '0.26M weights');

    // the push arrives from below
    el('line', {x1:924, y1:245, x2:924, y2:170, stroke:C.soft, 'stroke-width':3}, s);
    el('path', {d:'M924 152 l-10 18 h20 z', fill:C.soft}, s);
    el('text', {x:946, y:212, 'font-size':22, fill:C.ink, style:serif}, s, 'the push');

    arrow(s, 1034, y + bw / 2, 1114);
    latent(1124, 'the scene next', true);

    el('text', {x:0, y:290, 'font-size':17, fill:C.soft}, s,
       'No decoder: plans are compared as 192 numbers, never as pictures. Repeat the last two boxes to imagine further ahead.');
  })();

"""

anchor = '  // Navigation, notes and timer.'
if anchor not in html:
    sys.exit('could not find the navigation anchor in the script')
html = html.replace(anchor, FIG + anchor, 1)

OUT.write_text(html, encoding='utf-8')
print(f'wrote {OUT} ({len(html):,} bytes, {len(order)} slides)')

## Batch2 差异样本二次复核说明

这份文件用于解释当前 draft 与人工首轮判断之间的差异，帮助进行二次复核。

- 人工规则：用户列出的样本视为 `signal`，其余默认视为 `noise`
- 当前 draft 来源：`benchmark_samples_batch2_draft.json`
- 说明目标：把“为什么 draft 会这样判”先说清楚，再决定是否改成 `signal` 或调整类型

## A. 用户判为 signal，但 draft 不同

### B2D012

- 标题：Baldur's Gate 3 writer says its Dragon-Agey rep system is there to stop you totally breaking the NPCs, but it 'becomes a dice roll' at points to keep romance natural
- 你的判断：`signal` / `technical`
- 当前 draft：`noise` / `-`
- 来源：PC Gamer | 2026-03-23T00:00:00Z
- 链接：https://www.pcgamer.com/games/baldurs-gate/baldurs-gate-3-writer-says-its-dragon-agey-rep-system-is-there-to-stop-you-totally-breaking-the-npcs-but-it-becomes-a-dice-roll-at-points-to-keep-romance-natural/
- 摘要：Work smarter, not harder. Still insanely hard, though.
- 我为什么会这样倾向：
  - I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.
  - Heuristic scores: signal=1, noise=4, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; missing_game_context; very_short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D015

- 标题：Google's Gemini will make its way into Dragon Quest X to power a "Chatty Slimey" AI companion, Square Enix has announced
- 你的判断：`signal` / `technical`
- 当前 draft：`noise` / `-`
- 来源：Eurogamer | 2026-03-23T00:00:00Z
- 链接：https://www.eurogamer.net/google-gemini-ai-to-power-chatbot-companion-in-dragon-quest-x-square-enix-says
- 摘要：If you're still recovering from last week's DLSS 5 nightmare and Crimson Desert's gen-AI fiasco , we're sorry to re-open old wounds by telling you that Square Enix has announced it's teaming up with Google to put Gemini…
- 我为什么会这样倾向：
  - I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.
  - Heuristic scores: signal=5, noise=8, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:technical:1; hint:technical; high_value_entities:square enix,google; missing_game_context; low_information_excerpt; truncated_article; announcement_style; shallow_announcement_penalty.
  - Surface cues I would use on a quick pass: technical: ai, dlss.

### B2D028

- 标题：Union workers send a message to game industry execs: 'Let go of the power now, or be forced to let go of it later.'
- 你的判断：`signal` / `team`
- 当前 draft：`signal` / `technical`
- 来源：Game Developer | 2026-03-23T00:00:00Z
- 链接：https://www.gamedeveloper.com/production/union-workers-send-a-message-to-game-industry-execs-let-go-of-the-power-now-or-be-forced-to-let-go-of-it-later-
- 摘要：CWA members are staking their claim for a better, fairer video game industry.
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:technical; game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: team: union; technical: ai.

### B2D050

- 标题：Switch 2 demand appears to be flagging as Nintendo reportedly lowers production
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-24T00:00:00Z
- 链接：https://www.eurogamer.net/switch-2-flagging-nintendo-lowers-production
- 摘要：Year-one for Nintendo's Switch 2 began brightly , with early, record-breaking sales success. But a new report has suggested demand for Nintendo's newest console is flagging, especially in the US. Read more
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=7, noise=3, boundary=4.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:2; hint:technical; high_value_entities:nintendo; game_context; low_information_excerpt; boundary_patterns:1; rumor_or_report_sourcing; truncated_article.
  - Surface cues I would use on a quick pass: market: sales, demand.

### B2D057

- 标题：Pokémon Champions is releasing on Nintendo Switch consoles in early April, but its "free-to-start" package raises some questions about its pricing model
- 你的判断：`signal` / `market`
- 当前 draft：`noise` / `-`
- 来源：Eurogamer | 2026-03-25T00:00:00Z
- 链接：https://www.eurogamer.net/pokemon-champions-sets-release-date-and-details-free-to-play-model
- 摘要：2026 has just started, but Pokémon's 30th anniversary has already given us a winner in Pokémon Pokopia , the announcement of Winds & Waves , and even more reveals . But we're not done yet: yesterday, The Pokémon Company…
- 我为什么会这样倾向：
  - I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.
  - Heuristic scores: signal=5, noise=8, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:capital:1; hint:capital; high_value_entities:nintendo; game_context; noise_patterns:1; low_information_excerpt; truncated_article; announcement_style; shallow_announcement_penalty.
  - Surface cues I would use on a quick pass: technical: ai, model.

### B2D100

- 标题：Neuralink patient raiding in World of Warcraft after only 100 days of having the implant installed calls it 'pure magic… exploring Azeroth hands-free at full speed'
- 你的判断：`signal` / `technical`
- 当前 draft：`noise` / `-`
- 来源：PC Gamer | 2026-03-26T00:00:00Z
- 链接：https://www.pcgamer.com/games/world-of-warcraft/neuralink-patient-raiding-in-world-of-warcraft-after-only-100-days-of-having-the-implant-installed-calls-it-pure-magic-exploring-azeroth-hands-free-at-full-speed/
- 摘要："No mouse, no keyboard, just intention."
- 我为什么会这样倾向：
  - I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.
  - Heuristic scores: signal=1, noise=4, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; missing_game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D101

- 标题：PlayStation Store's rumoured "dynamic pricing" has reportedly been spotted in the wild, and the differences appear to be huge
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-26T00:00:00Z
- 链接：https://www.eurogamer.net/playstation-store-dynamic-pricing-reportedly-spotted-march-2026
- 摘要：Something's happening behind the PlayStation Store's front. Earlier this month, we learned that Sony appears to be testing "dynamic pricing" for users in some territories . This could affect both first-party and third-p…
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=3, boundary=4.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:sony,playstation; game_context; low_information_excerpt; boundary_patterns:1; rumor_or_report_sourcing; truncated_article.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D102

- 标题：The Expanse: Osiris Reborn Gets a Debut Gameplay Trailer With Big Mass Effect Vibes, a Closed Beta, and a Spring 2027 Release Window
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-26T00:00:00Z
- 链接：https://www.ign.com/articles/the-expanse-osiris-reborn-gets-a-debut-gameplay-trailer-with-big-mass-effect-vibes-a-closed-beta-and-a-spring-2027-release-window
- 摘要：The Expanse: Osiris Reborn is making a big splash with a slew of announcements, all revolving around its first gameplay trailer.
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:technical; game_context; noise_patterns:1; short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D112

- 标题：Magic's TMNT Draft Night Box Is Discounted For Amazon's Big Spring Sale
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-27T00:00:00Z
- 链接：https://www.ign.com/articles/magics-tmnt-draft-night-box-is-discounted-for-amazons-big-spring-sale
- 摘要：Amazon has plenty of Magic: The Gathering deals right now as part of its Big Spring Sale, including the TMNT Draft Night box for about $40 off the regular price.
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: market: price.

### B2D121

- 标题：Unity sunsetting Ads Network and divesting publishing label Supersonic
- 你的判断：`signal` / `capital`
- 当前 draft：`signal` / `technical`
- 来源：Game Developer | 2026-03-27T00:00:00Z
- 链接：https://www.gamedeveloper.com/business/unity-sunsetting-ads-network-and-divesting-publishing-label-supersonic
- 摘要：The company has claimed jettisoning both businesses will help drive revenue growth.
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:unity; game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai; market: revenue.

### B2D146

- 标题：Clair Obscur: Expedition 33 devs never imagined to achieve the kind of massive success it did: 'Our official goal towards the end of production was to reach for 85 in Metacritic'
- 你的判断：`signal` / `technical`
- 当前 draft：`noise` / `-`
- 来源：PC Gamer | 2026-03-30T00:00:00Z
- 链接：https://www.pcgamer.com/games/rpg/clair-obscur-expedition-33-devs-never-imagined-to-achieve-the-kind-of-massive-success-it-did-our-official-goal-towards-the-end-of-production-was-to-reach-for-85-in-metacritic/
- 摘要：Shoot for the moon and you'll land among the stars.
- 我为什么会这样倾向：
  - I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.
  - Heuristic scores: signal=2, noise=4, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:meta; missing_game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D152

- 标题：Remember when Mastercard pressured Steam to remove a bunch of NSFW games? The FTC says that's not cool—sort of
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：PC Gamer | 2026-03-30T00:00:00Z
- 链接：https://www.pcgamer.com/games/remember-when-mastercard-pressured-steam-to-remove-a-bunch-of-nsfw-games-the-ftc-says-thats-not-cool-sort-of/
- 摘要：The FTC warned Mastercard, PayPal, and others against denying consumers the right to buy what they want, saying that "access to such infrastructure and services is essential for Americans’ participation in everyday comm…
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai; market: steam.

### B2D161

- 标题：Cancellation Of Almost-Complete Game From Eidos Montreal Resulted In Layoffs - Report
- 你的判断：`signal` / `capital, team`
- 当前 draft：`signal` / `team`
- 来源：GameSpot | 2026-03-31T00:00:00Z
- 链接：https://www.gamespot.com/articles/cancellation-of-almost-complete-game-from-eidos-montreal-resulted-in-layoffs-report/1100-6539139/?ftag=CAD-01-10abi2f
- 摘要：Recent mass layoffs at developer Eidos Montreal were the result of a long-in-development project at the studio that was close to completion being canceled, according to a new report. As reported by Insider Gaming , the …
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=10, noise=0, boundary=8.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:2; signal_pattern:market:1; hint:team; game_context; boundary_patterns:3; rumor_or_report_sourcing; structural_change_keywords.
  - Surface cues I would use on a quick pass: team: layoff.

### B2D166

- 标题：Disney could be interested in buying Fortnite maker Epic Games, but not everyone's on board with the idea
- 你的判断：`signal` / `capital`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-31T00:00:00Z
- 链接：https://www.eurogamer.net/disney-could-be-looking-into-buying-fortnite-developer-epic-games
- 摘要：Fortnite maker Epic Games has had a rough start to the year, with Fortnite's players dropping noticeably , and now over 1,000 jobs being cut as a result. Now, there's talk of entertainment giant Disney looking to buy th…
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=3, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:epic,disney; game_context; low_information_excerpt; boundary_patterns:1; truncated_article.
  - Surface cues I would use on a quick pass: technical: ai; market: players.

### B2D173

- 标题：Price Hike or Discount? Nintendo's Changes to Physical and Digital Game Pricing Have Analysts Split, Too
- 你的判断：`signal` / `market`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-31T00:00:00Z
- 链接：https://www.ign.com/articles/price-hike-or-discount-nintendos-changes-to-physical-and-digital-game-pricing-have-analysts-split-too
- 摘要：Nintendo games are about to get more expensive. Or less. Depending on whether or not you want a physical copy, and how you read its recent decision to charge different prices for physical and digital games in the U.S. W…
- 我为什么会这样倾向：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:nintendo; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: market: price.

## B. draft 判为 signal，但用户本轮未列出（按当前规则默认应为 noise）

这些样本不是说 draft 一定正确，而是它们在当前启发式中被保留为 signal；如果下面理由没有说服力，就应降为 noise。

### B2D002

- 标题：God is dead and I am a bullet hell boss of my own making in the physics-based dicerolling roguelike DeeSicks
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-21T00:00:00Z
- 链接：https://www.rockpapershotgun.com/god-is-dead-and-i-am-a-bullet-hell-boss-of-my-own-making-in-the-physics-based-dicerolling-roguelike-deesicks
- 摘要：I'm going to say it: bullet hells are more stressful than Souls-likes. Why are there 10,000 orbs approaching me, promising me misery and death! And I have to both tactfully dodge them while also staging a front myself? …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D003

- 标题：If you ask Yoshi-P, kids don't care about Final Fantasy anymore because they're taking too long to come out
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-21T00:00:00Z
- 链接：https://www.rockpapershotgun.com/if-you-ask-yoshi-p-kids-dont-care-about-final-fantasy-anymore-because-theyre-taking-too-long-to-come-out
- 摘要：Last month, a post caught some kind of virus and did the rounds, pondering why kids don't care about Final Fantasy or Dragon Quest so much anymore, wondering what they do plan now, and anecdotally findering that most of…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D007

- 标题：Resident Evil Requiem Kills The Past So The Series Can Move Forward
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：GameSpot | 2026-03-23T00:00:00Z
- 链接：https://www.gamespot.com/articles/resident-evil-requiem-kills-the-past-so-the-series-can-move-forward/1100-6538964/?ftag=CAD-01-10abi2f
- 摘要：Warning! This post contains spoilers for the entirety of Resident Evil Requiem's story, as well as some spoilers for the larger Resident Evil canon. Finish the game before you read this. You don't get Resident Evil Requ…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:capital; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D013

- 标题：Diablo 4 Season 12's Greatest Challenge Is Being Nerfed "Significantly"
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-23T00:00:00Z
- 链接：https://www.gamespot.com/articles/diablo-4-season-12-greatest-challenge-is-being-nerfed-significantly/1100-6538955/?ftag=CAD-01-10abi2f
- 摘要：Diablo 4's Season of Slaughter brought new, bloody challenges to Blizzard's ARPG, among them one so difficult that many players couldn't "reasonably" complete it. As detailed in Diablo 4's most recent patch notes , an u…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: technical: ai; market: players.

### B2D014

- 标题：Dragon's Dogma 2 Fans Are Convinced Capcom Is Teasing An Expansion
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-23T00:00:00Z
- 链接：https://www.gamespot.com/articles/dragons-dogma-2-fans-are-convinced-capcom-is-teasing-an-expansion/1100-6538950/?ftag=CAD-01-10abi2f
- 摘要：Capcom's 2024 open-world RPG Dragon's Dogma 2 could be set to follow in the footsteps of its predeccesor with a major expansion, with the game's community convinced a recent piece of artwork celebrating the game's secon…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=7, noise=4, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:technical; high_value_entities:epic,capcom,unity; game_context; noise_patterns:2; boundary_patterns:1.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D017

- 标题：I love the pulpy floral palace of Journey of the Garden Rose, a 3D action fairytale with giant insect swordfights
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-23T00:00:00Z
- 链接：https://www.rockpapershotgun.com/i-love-the-pulpy-floral-palace-of-journey-of-the-garden-rose-a-3d-action-fairytale-with-giant-insect-swordfights
- 摘要：Get in the videogame, loser, it's time to break into an "impossible palace", stab insect gardeners with your saber, and rescue your mother from some bastard prince. Out today, Journey Of The Garden Rose is the latest "o…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D018

- 标题：Peter Molyneux's Masters of Albion looks to have everything I love about those Bullfrog and Lionhead classics, but the scepticism is hard to shake
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-23T00:00:00Z
- 链接：https://www.eurogamer.net/masters-of-albion-looks-to-have-everything-i-love-in-those-bullfrog-and-lionhead-classics
- 摘要：Few developers can - even after all this time - get you quite so swept up in their enthusiasm as Peter Molyneux. It's an enthusiasm that has, famously, got him into trouble in the past, when passion and promise have fai…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; announcement_style.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D019

- 标题：Pokemon Pokopia Players Are Building Incredibly Complex Creations
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-23T00:00:00Z
- 链接：https://www.gamespot.com/articles/pokemon-pokopia-players-are-building-incredibly-complex-creations/1100-6538948/?ftag=CAD-01-10abi2f
- 摘要：Pokemon Pokopia was created to give players the opportunity to build a comfortable home for their Pokemon, but some fans are already pushing the game's ability to craft and create to another level. At least two players …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:unity; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: market: players.

### B2D023

- 标题：Super Mario Galaxy Movie's Big Canon Reveal Seemingly Spoiled by Ratings Board Listing
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-23T00:00:00Z
- 链接：https://www.ign.com/articles/super-mario-galaxy-movies-big-canon-reveal-seemingly-spoiled-by-ratings-board-listing
- 摘要：A huge plot point from The Super Mario Galaxy Movie — and indeed, all of Nintendo canon — looks to have been spoiled by a ratings board listing.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context; short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D026

- 标题：This week in PC games: a new Hooded Horse city-builder, some PS2-style horror, a school-day RPG and an absolutely tremendous catfish
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-23T00:00:00Z
- 链接：https://www.rockpapershotgun.com/this-week-in-pc-games-a-new-hooded-horse-city-builder-some-ps2-style-horror-a-school-day-rpg-and-an-absolutely-tremendous-catfish
- 摘要：Urgh! What's happening? The air feels dreadfully recycled all of a sudden. Food dissatisfies, music grates, punchlines flop like stunned seagulls - everything seems somehow overfamiliar . We have entered a Lull. There a…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D030

- 标题：Your citizens don't stay put in Stellaris-style 4X strategy game Final Vanguard - start a war and "entire waves of refugees can emerge"
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-23T00:00:00Z
- 链接：https://www.rockpapershotgun.com/your-citizens-dont-stay-put-in-stellaris-style-4x-strategy-game-final-vanguard-start-a-war-and-entire-waves-of-refugees-can-emerge
- 摘要：Final Vanguard is a real-time sci-fi 4X grand strategy game that puts an unusually big emphasis on migration. We've seen migration mechanics in many 4X games – pops can shuffle about in Stellaris as you slop your coloni…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D033

- 标题：Screen Australia hands out $1.4 million to local developers
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：Game Developer | 2026-03-24T00:00:00Z
- 链接：https://www.gamedeveloper.com/business/screen-australia-hands-out-1-4-million-to-local-developers
- 摘要：The financing will support 26 projects 'centered on Australian stories and ideas.'
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:capital; game_context; concrete_numbers; very_short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D034

- 标题：'We've Sportified Steam Charts' — Warframe Creative Director Rebecca Ford Reveals How Digital Extremes Is Keeping the Live Service Dream Alive
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：IGN Game News | 2026-03-24T00:00:00Z
- 链接：https://www.ign.com/articles/weve-sportified-steam-charts-warframe-creative-director-rebecca-ford-reveals-how-digital-extremes-is-keeping-the-live-service-dream-alive
- 摘要：Warframe interview with creative director Rebecca Ford on Steam charts obsession, upcoming updates, and the Nintendo Switch 2 version.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; high_value_entities:nintendo; game_context; noise_patterns:1; short_excerpt.
  - Surface cues I would use on a quick pass: market: steam.

### B2D037

- 标题：Pokémon Champions Launches Next Month With Paid Upgrade Pack to 'Support Early Progression'
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：IGN Game News | 2026-03-24T00:00:00Z
- 链接：https://www.ign.com/articles/pokemon-champions-launches-next-month-with-paid-upgrade-pack-to-support-early-progression
- 摘要：The Pokémon Company has announced a Nintendo Switch and Switch 2 release date for its upcoming free-to-play battler Pokémon Champions, alongside a paid starter pack which provides "useful in-game items."
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:market; high_value_entities:nintendo; game_context; announcement_style.
  - Surface cues I would use on a quick pass: technical: ai; market: launch.

### B2D038

- 标题：The Newest Payday Game Is Unexpected, And I Hope It's Better Than Payday 3
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：GameSpot | 2026-03-24T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-newest-payday-game-is-unexpected-and-i-hope-its-better-than-payday-3/1100-6538956/?ftag=CAD-01-10abi2f
- 摘要：A new Payday has been announced for virtual reality platforms. As the first new game in the series since the disappointing launch of Payday 3 , Payday: Aces High will certainly face a high level of scrutiny at launch. P…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; announcement_style.
  - Surface cues I would use on a quick pass: technical: ai; market: launch.

### B2D042

- 标题：Sony Shuts Down Former CoD Dev's Studio Amid Wider Cuts
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：GameSpot | 2026-03-24T00:00:00Z
- 链接：https://www.gamespot.com/articles/sony-shuts-down-former-cod-devs-studio-amid-wider-cuts/1100-6538989/?ftag=CAD-01-10abi2f
- 摘要：Dark Outlaw Games, the studio founded by former Call of Duty developer Jason Blundell, is shutting down amid bigger cuts to PlayStation overall, according to a report from Jason Schreier. Blundell's previous studio, Dev…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=0, boundary=4.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:team; high_value_entities:sony,playstation; game_context; boundary_patterns:2.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D043

- 标题：13 Years of Warframe: The Shadowgrapher Update, Nintendo Switch 2 Version, and Plenty More to Come
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-24T00:00:00Z
- 链接：https://www.ign.com/articles/13-years-of-warframe-the-shadowgrapher-update-nintendo-switch-2-version-and-plenty-more-to-come
- 摘要：Warframe creative director Rebecca Ford explains the enduring appeal of the free-to-play action-RPG as it turns 13.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D044

- 标题：As seminal oddball indie Superbrothers: Sword & Sworcery EP hits 15 years of age, you can pick it up for less than a coffee
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-24T00:00:00Z
- 链接：https://www.rockpapershotgun.com/as-seminal-oddball-indie-superbrothers-sword-sworcery-ep-hits-15-years-of-age-you-can-pick-it-up-for-less-than-a-coffee
- 摘要：Let's travel back in time, roughly to the late 2000s and early 2010s. It was a time where indie games were becoming more of a defined Separate Thing from blockbuster games. It certainly wasn't the birth of indie games, …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D045

- 标题：Fortnite developer Epic Games is cutting over 1,000 jobs
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Game Developer | 2026-03-24T00:00:00Z
- 链接：https://www.gamedeveloper.com/business/fortnite-developer-epic-games-is-cutting-1-000-jobs
- 摘要：Epic boss Tim Sweeney shared the news with employees while acknowledging Fortnite remains 'one of the most successful games in the world.'
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:epic; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: team: employees; technical: ai.

### B2D046

- 标题：Marvel Rivals Devs Won't Introduce Original Characters Anytime Soon, Because There Are Simply Too Many Marvel Characters Already
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-24T00:00:00Z
- 链接：https://www.ign.com/articles/marvel-rivals-devs-wont-introduce-original-characters-anytime-soon-because-there-are-simply-too-many-marvel-characters-already
- 摘要：NetEase Games isn't worried about balance in Marvel Rivals as its roster expands with more playable heroes, but don't expect to see any original characters anytime soon.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:netease; game_context; short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D048

- 标题：Payday: Aces High Is a New 4-Player Co-op VR Game Coming to Steam and Meta Where You Can 'Pull Off Daring Jobs in VR Using Black-Market Tech'
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-24T00:00:00Z
- 链接：https://www.ign.com/articles/payday-aces-high-is-a-new-4-player-co-op-vr-game-coming-to-steam-and-meta-where-you-can-pull-off-daring-jobs-in-vr-using-black-market-tech
- 摘要：Payday Announces VR Game
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:meta; game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: market: market, steam.

### B2D058

- 标题：The Ghost In The Shell Legacy Edition Manga Set Is Steeply Discounted Right Now
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-ghost-in-the-shell-legacy-edition-manga-set-is-steeply-discounted-right-now/1100-6539020/?ftag=CAD-01-10abi2f
- 摘要：The Ghost in the Shell Legacy Edition Manga Box Set $107 (was $140) See at Amazon Ghost in the Shell is one of the most important franchises in manga and anime. The series began as a manga created by Masamune Shirow, wh…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:capital; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D059

- 标题：EverQuest Legends Boasts 'All The Magic And Nostalgia of Classic EverQuest' With a Modern Twist
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：IGN Game News | 2026-03-25T00:00:00Z
- 链接：https://www.ign.com/articles/everquest-legends-boasts-all-the-magic-and-nostalgia-of-classic-everquest-with-a-modern-twist
- 摘要：A "fan-driven collaboration designed to give players a new way" to play EverQuest is on the way: EverQuest Legends.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: market: players.

### B2D060

- 标题：Marathon may have sold roughly 1.2m copies worldwide, with the majority on Steam rather than PlayStation, according to analyst estimates
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：Eurogamer | 2026-03-25T00:00:00Z
- 链接：https://www.eurogamer.net/marathon-may-have-sold-roughly-12m-copies-worldwide-with-the-majority-on-steam-rather-than-playstation-according-to-analyst-estimates
- 摘要：Marathon may have surpassed 1.2m sales worldwide according to analyst estimations. Of that number, the majority appear to be present on PC, rather than PlayStation. Read more
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=7, noise=3, boundary=5.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; high_value_entities:playstation; game_context; low_information_excerpt; boundary_patterns:2; concrete_numbers; short_excerpt; truncated_article.
  - Surface cues I would use on a quick pass: market: sales, sold, copies, steam.

### B2D062

- 标题：The Best Deals On Razer Gaming Accessories In Amazon's Spring Sale
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/articles/amazon-spring-sale-razer-deals/1100-6538993/?ftag=CAD-01-10abi2f
- 摘要：Just about everything related to PC and console gaming seems to be increasing in price lately, but fortunately, these Amazon Spring Sale deals on Razer products are a welcome exception to that rule. Razer has establishe…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: market: price.

### B2D063

- 标题：Fortnite developers say there will be a huge impact on development "for the rest of the year and likely beyond" following mass layoffs
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：Eurogamer | 2026-03-25T00:00:00Z
- 链接：https://www.eurogamer.net/fortnite-producer-comments-on-mass-layoffs-march-2026
- 摘要：Fortnite is one of the biggest games in the world, so it isn't overly surprising to see Epic Games make adjustments to how the title is run as the game nears its tenth birthday. Maintaining a massive multiplatform opera…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=7, noise=5, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:team; high_value_entities:epic; game_context; noise_patterns:1; low_information_excerpt; truncated_article; structural_change_keywords.
  - Surface cues I would use on a quick pass: team: layoff; technical: ai.

### B2D064

- 标题：Hideo Kojima's Focus For Death Stranding 2 Was Ensuring Fans Enjoyed It 'All the Way to the End'
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：IGN Game News | 2026-03-25T00:00:00Z
- 链接：https://www.ign.com/articles/hideo-kojimas-focus-for-death-stranding-2-was-ensuring-fans-enjoyed-it-all-the-way-to-the-end
- 摘要：Hideo Kojima stressed to his team that he wanted to ensure that players jumping into Death Stranding 2: On the Beach would have a great time "all the way to the end."
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:team; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: market: players.

### B2D066

- 标题：Sony shutters internal studio Dark Outlaw Games
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：Game Developer | 2026-03-25T00:00:00Z
- 链接：https://www.gamedeveloper.com/business/playstation-shutters-internal-studio-dark-outlaw-games
- 摘要：The PlayStation studio was established by Call of Duty veteran Jason Blundell in 2024.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:team; high_value_entities:sony,playstation; game_context; very_short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D067

- 标题：37 Things You Didn't Know In Crimson Desert
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/videos/37-things-you-didnt-know-in-crimson-desert/2300-6466788/
- 摘要：We cover 37 simple and complex tips, tricks, and facts in Crimson Desert that aren’t quite as well known. The recently released Crimson Desert has a massive world with endless possibilities, and we're only starting to s…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D068

- 标题：Amazon’s Has a Bunch of New Magic: The Gathering Deals as Part of Its Spring Sale
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-25T00:00:00Z
- 链接：https://www.ign.com/articles/amazons-has-a-bunch-of-new-magic-the-gathering-deals-as-part-of-its-spring-sale
- 摘要：From Commander decks to booster boxes, here are the best deals in Magic during Amazon's sales event.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; noise_patterns:1; short_excerpt.
  - Surface cues I would use on a quick pass: market: sales.

### B2D072

- 标题：Get $100 Worth Of Robux For $80 Right Now
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/articles/get-100-worth-of-robux-for-80-right-now/1100-6539019/?ftag=CAD-01-10abi2f
- 摘要：Roblox is one of the most popular games on the planet, and if you're looking to stock up on the game's in-game currency, Robux, Amazon's Big Spring Sale has a nice offer to consider. As part of the sale, Amazon is offer…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D077

- 标题：Nintendo Clarifies 'The Cost of Physical Games Is Not Going Up' Following Decision to Charge Different Prices for U.S. Physical and Digital Switch 2 Games
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-25T00:00:00Z
- 链接：https://www.ign.com/articles/nintendo-switch-2-physical-games-will-now-be-more-expensive-than-digital-versions-with-10-price-difference-for-yoshi-and-the-mysterious-book
- 摘要：Nintendo has announced that it will now charge different amounts for digital and physical copies of the same Switch 2 games, beginning with next month's launch of Yoshi and the Mysterious Book.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context; announcement_style.
  - Surface cues I would use on a quick pass: market: copies, price, launch.

### B2D078

- 标题：Save On Xbox Controller Deals During Amazon's Spring Sale
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/articles/amazon-spring-sale-xbox-controller-deals/1100-6538995/?ftag=CAD-01-10abi2f
- 摘要：The current Xbox wireless controller is one of the best gaming peripherals, and with the Amazon Spring Sale , you can save on this device. Normally $65 for the Carbon Black version, it's now $45, and several other color…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:xbox; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D081

- 标题：This Mario-Themed Switch Controller Is Only $30 Right Now
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-25T00:00:00Z
- 链接：https://www.gamespot.com/articles/this-mario-themed-switch-controller-is-only-30-right-now/1100-6539013/?ftag=CAD-01-10abi2f
- 摘要：Amazon's Big Spring Sale is underway, and there are numerous offers available on all manner of products. One nice deal you can grab right now is for PowerA's Mario-themed Switch controllers. Get on Amazon The PowerA wir…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D083

- 标题：Netflix Is Getting More Expensive, And That Impacts Games, Too
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：GameSpot | 2026-03-26T00:00:00Z
- 链接：https://www.gamespot.com/articles/netflix-is-getting-more-expensive-and-that-impacts-games-too/1100-6539050/?ftag=CAD-01-10abi2f
- 摘要：Netflix has raised the prices of all three of its subscription tiers again. Whether you use the service to watch TV and movies or play video games, this will impact you. Variety spotted that Netflix had modified its sub…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:capital; game_context.
  - Surface cues I would use on a quick pass: technical: ai; market: price.

### B2D084

- 标题：STALKER 2: Cost of Hope is a "massive nonlinear expansion" that includes the Chornobyl power plant visit the base game never made time for
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：Rock Paper Shotgun | 2026-03-26T00:00:00Z
- 链接：https://www.rockpapershotgun.com/stalker-2-cost-of-hope-expansion-announced
- 摘要：STALKER 2: Heart of Chornobyl is getting its first proper expansion this year, titled Cost of Hope, and it looks stuffed to its icky mutant gills with classic STALKER series beats that the base game – while a powerfully…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:capital; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D087

- 标题：Island city-builder Nova Roma releases today, and I'd have drowned all my Romans already if it weren't for those pesky gods
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：Rock Paper Shotgun | 2026-03-26T00:00:00Z
- 链接：https://www.rockpapershotgun.com/island-city-builder-nova-roma-releases-today-and-id-have-drowned-all-my-romans-already-if-it-werent-for-those-pesky-gods
- 摘要：I have two dreams as mayor of an island town in Nova Roma , the new early access city-building game from Lion Shield and Hooded Horse. One is to erect a fantastic water network for my people - a sturdy yet poetic lattic…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:market; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D088

- 标题：Save On Select Magic: The Gathering Lorwyn Eclipse Releases This Week
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：GameSpot | 2026-03-26T00:00:00Z
- 链接：https://www.gamespot.com/articles/save-on-select-magic-the-gathering-lorwyn-eclipse-releases-this-week/1100-6539054/?ftag=CAD-01-10abi2f
- 摘要：If you're looking to fill out your backlog of Magic: The Gathering sets, you'll want to check out these limited-time deals on Lorwyn Eclipsed Commander decks and booster boxes at Amazon . The Lorwyn Eclipsed set launche…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: market: launch.

### B2D089

- 标题：The Legend of Zelda: Tears of the Kingdom Scores a Rare $20 Discount in Spring Sales
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：IGN Game News | 2026-03-26T00:00:00Z
- 链接：https://www.ign.com/articles/the-legend-of-zelda-tears-of-the-kingdom-scores-a-rare-20-discount-in-spring-sales
- 摘要：## 我的判断 > （移到 05-Insights 前在这里写下你的想法，并添加 signal_type frontmatter） --- auto-collected 2026-03-27 08:00
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; noise_patterns:1; short_excerpt.
  - Surface cues I would use on a quick pass: market: sales.

### B2D091

- 标题：Vaunted Is A Tactical RPG Where You Can’t Trust Your Own Team
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：GameSpot | 2026-03-26T00:00:00Z
- 链接：https://www.gamespot.com/articles/vaunted-is-a-tactical-rpg-where-you-cant-trust-your-own-team/1100-6539006/?ftag=CAD-01-10abi2f
- 摘要：Today's Xbox Partner Preview was focused purely on third-party studios, and one of the brand-new games in the spotlight was Vaunted from Lost Lake Games. A tactical-RPG that challenges players to seize the ultimate scor…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:team; high_value_entities:xbox; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: market: players.

### B2D093

- 标题："At this rate, why make game art at all?": Nvidia DLSS 5 demands a sale damaging and stock tanking fightback, argues New Blood boss
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-26T00:00:00Z
- 链接：https://www.rockpapershotgun.com/at-this-rate-why-make-game-art-at-all-nvidia-dlss-5-demands-a-sale-damaging-and-stock-tanking-fightback-argues-new-blood-boss
- 摘要：Players and developers should boycott Nvidia's AI-stuffed DLSS 5 tech , with hopes that it'll force the compny to "think about going back to giving us what we want". That's the appeal being made by Dave Oshry, CEO of in…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=3, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:technical:1; signal_pattern:market:1; hint:technical; game_context; low_information_excerpt; truncated_article.
  - Surface cues I would use on a quick pass: team: ceo; technical: ai, dlss; market: demand, players.

### B2D094

- 标题："Everything in the final version will definitely 100% be human made" - But Owlcat says gen-AI is being used during The Expanse: Osiris Reborn development
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-26T00:00:00Z
- 链接：https://www.eurogamer.net/owlcat-gen-ai-expanse-osiris-reborn
- 摘要：The Expanse: Osiris Reborn developer Owlcat - known for making Pathfinder: Kingmaker, Pathfinder: Wrath of the Righteous, and Warhammer 40K: Rogue Trader - has confirmed it is using generative AI during the sci-fi game'…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=3, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:technical:2; hint:technical; game_context; low_information_excerpt; truncated_article.
  - Surface cues I would use on a quick pass: technical: ai, generative ai.

### B2D095

- 标题：For better or worse, Max and Chloe are together again in Life is Strange: Reunion, which is out right now
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-26T00:00:00Z
- 链接：https://www.rockpapershotgun.com/for-better-or-worse-max-and-chloe-are-together-again-in-life-is-strange-reunion-which-is-out-right-now
- 摘要：A new Life is Strange game doesn't always feel particularly odd given its sort of steady turn into a franchise. The last one was only in 2024 with Life Is Strange: Double Exposure, bringing back the original game's Max …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: team: union; technical: ai.

### B2D096

- 标题：Forza Horizon 6 system requirements confirm it’s no RAM guzzler - and it’ll run on Steam Deck too
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-26T00:00:00Z
- 链接：https://www.rockpapershotgun.com/forza-horizon-6-system-requirements-confirm-its-no-ram-guzzler-and-itll-run-on-steam-deck-too
- 摘要：Perhaps sensing competition in the field of Japan-flavoured arcade racing games , Forza Horizon 6 devs Playground Games have revealed the open-world vroomer’s system requirements. Agreeably, they’re a sensible balance o…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: market: steam.

### B2D103

- 标题：Slay the Spire 2 Dev Adjusts Update That Led To Review Bombing
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/slay-the-spire-2-dev-adjusts-update-that-led-to-review-bombing/1100-6539079/?ftag=CAD-01-10abi2f
- 摘要：Earlier this month, Mega Crit shared the first major update for Slay the Spire 2 , which included nerfs and buffs that angered some players enough to review bomb the game . Now, Mega Crit is rolling back some of those c…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:capital; game_context; noise_patterns:1; boundary_patterns:1.
  - Surface cues I would use on a quick pass: market: players.

### B2D106

- 标题：Slay the Spire 2's 'anti-infinite' balance patch has now itself been patched, much to the relief of some Silent and Necrobinder players
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：Rock Paper Shotgun | 2026-03-27T00:00:00Z
- 链接：https://www.rockpapershotgun.com/slay-the-spire-2s-anti-infinite-balance-patch-has-now-itself-been-patched-much-to-the-relief-of-some-silent-and-necrobinder-players
- 摘要：Slay the Spire 2 developers Mega Crit have rolled back aspects of last week's big STS2 balancing update , which nerfed a number of cards according to the broad objective of making infinites – that is, cunning combos tha…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=0, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:market; game_context; boundary_patterns:1.
  - Surface cues I would use on a quick pass: market: players.

### B2D107

- 标题：Boy, There Sure Was A Lot Of Bad News This Week, Right?
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/boy-there-sure-was-a-lot-of-bad-news-this-week-right/1100-6539070/?ftag=CAD-01-10abi2f
- 摘要：The final full week of March is coming to a close, and it has been a rollercoaster of emotions if you've been following the recent gaming news. Between showcases and turmoil in the industry, you never know what you're i…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:team; game_context; noise_patterns:1.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D108

- 标题：The New PUBG Game Is Closing After Less Than 2 Months
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-new-pubg-game-is-closing-after-less-than-2-months/1100-6539078/?ftag=CAD-01-10abi2f
- 摘要：Near the beginning of February, Krafton gave an early-access release to PUBG: Blindspot , a spin-off from PlayerUnknown's Battlegrounds . However, Blindspot won't make it to its two-month anniversary as the game is sche…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:1; hint:team; game_context; noise_patterns:1.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D109

- 标题：'I Don't Really Want to Do That Again' - Baldur's Gate 3's Astarion Doesn't Want to Keep Rehashing the Same Type of Roles
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-27T00:00:00Z
- 链接：https://www.ign.com/articles/i-dont-really-want-to-do-that-again-baldurs-gate-3s-astarion-doesnt-want-to-keep-rehashing-the-same-type-of-roles
- 摘要：Neil Newbon's performance as Astarion in Baldur's Gate 3 is among the most memorable in the game, and that's saying a lot given how many amazing actors are in there cooking. Newbon's clearly proud of the good work he di…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D113

- 标题：Magic: The Gathering's Lord of the Rings Scene Boxes Are Back on Sale at Amazon
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-27T00:00:00Z
- 链接：https://www.ign.com/articles/magic-the-gathering-lord-of-the-rings-scene-boxes-are-back-on-sale-at-amazon
- 摘要：One of the best deals we've spotted amongst the many Magic: The Gathering deals is for the full set of Scene Boxes from The Lord of the Rings: Tales of Middle-earth set, which is currently on sale for $60 off its regula…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; noise_patterns:1.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D116

- 标题：Pragmata Contains a Stage That's a 'Fake New York Generated by AI,' but It's Entirely Made by Humans
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-27T00:00:00Z
- 链接：https://www.ign.com/articles/pragmata-contains-a-stage-thats-a-fake-new-york-generated-by-ai-but-its-entirely-made-by-humans
- 摘要：In the latest interview from the dev team behind Pragmata, they said that they're hand-crafting one of the levels in the game to look like it was AI-generated, despite it being fully made by humans.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:technical:1; hint:technical; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D117

- 标题：Sony confirms PS5 hardware is about to become even more expensive
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Game Developer | 2026-03-27T00:00:00Z
- 链接：https://www.gamedeveloper.com/console/sony-confirms-ps5-hardware-is-about-to-become-more-expensive
- 摘要：A global price hike will be implemented on April 2, 2026.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:sony; game_context; very_short_excerpt.
  - Surface cues I would use on a quick pass: market: price.

### B2D118

- 标题：Super Smash Bros. Amiibo Figures Are Discounted At Target
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/super-smash-bros-series-amiibo-at-target/1100-6539072/?ftag=CAD-01-10abi2f
- 摘要：One of the coolest--and most affordable--Nintendo collectibles you can get right now is an Amiibo. These miniature figures capture the likeness of Nintendo's many recognizable characters from series like Super Mario, Ki…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D119

- 标题：The Super Mario Galaxy Movie Recruited A Top Gun To Voice Fox McCloud
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-super-mario-galaxy-movie-recruited-a-top-gun-to-voice-fox-mccloud/1100-6539068/?ftag=CAD-01-10abi2f
- 摘要：It's official: Running Man star Glen Powell is the voice of Fox McCloud in The Super Mario Galaxy Movie . Earlier this week, Nintendo revealed that the ace pilot of the Star Fox series will appear in the sequel to The S…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D123

- 标题：Amazon Spring Sale - Grab This Commodore 64 Replica Console For Just $85
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-27T00:00:00Z
- 链接：https://www.gamespot.com/articles/amazon-spring-sale-grab-this-commodore-64-replica-console-for-just-85/1100-6539039/?ftag=CAD-01-10abi2f
- 摘要：In the earliest days of PC gaming, before everything got homogenized with Windows and Mac, the Commodore 64 reigned supreme. It still has a passionate homebrew community making their own original C64 games to this day--…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:unity; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D124

- 标题：Wanderstop studio Ivy Road to close after funding for second game "didn't come to fruition"
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `capital`
- 来源：Eurogamer | 2026-03-28T00:00:00Z
- 链接：https://www.eurogamer.net/wanderstop-studio-ivy-road-to-close-after-funding-for-second-game-didnt-come-to-fruition
- 摘要：Ivy Road, the studio formed by talent behind games like The Stanley Parable , Gone Home , and Minecraft, is closing down. Read more
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `capital`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=6, noise=3, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:capital:1; signal_pattern:team:1; hint:capital; game_context; low_information_excerpt; short_excerpt; truncated_article.
  - Surface cues I would use on a quick pass: capital: funding.

### B2D128

- 标题："I think it’s unfair to kind of geofence the genre": Original Stalker designer talks Eurojank in not-so-Euro games
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Rock Paper Shotgun | 2026-03-28T00:00:00Z
- 链接：https://www.rockpapershotgun.com/i-think-its-unfair-to-kind-of-geofence-the-genre-original-stalker-designer-talks-eurojank-in-not-so-euro-games
- 摘要：Video games, or more so the people who play them, I suppose, have this annoying thing where they assign a genre name as an insult. I don't want to reignite the discourse around JRPG as a term, but it certainly was used …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D136

- 标题：DLSS 5 Isn't Anywhere Near As Impressive As V-Rally 3 on the Game Boy Advance
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-29T00:00:00Z
- 链接：https://www.ign.com/articles/dlss-5-isnt-anywhere-near-as-impressive-as-v-rally-3-on-the-game-boy-advance
- 摘要：DLSS 5's AI generated game "enhancement" has gone down like a lead balloon in the gaming community. But there's plenty of love out there for the humble Game Boy Advance, a dinky little machine with a 16MHz processor tha…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=0, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:technical:1; hint:technical; high_value_entities:unity; game_context; boundary_patterns:1.
  - Surface cues I would use on a quick pass: technical: ai, dlss.

### B2D138

- 标题：I Bought a Nintendo Switch Lite in 2026...
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-29T00:00:00Z
- 链接：https://www.gamespot.com/videos/i-bought-a-nintendo-switch-lite-in-2026/2300-6466791/
- 摘要：The year is 2026 and Jake went out and bought a Nintendo Switch Lite. He explains why as he unboxes the special edition Dialga and Palkia console.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=3, noise=0, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:nintendo; game_context; short_excerpt.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D141

- 标题：Kena: Bridge of Spirits' Switch 2 port is fine, but doesn't offer an upgrade over handheld PC or last-gen experiences
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：Eurogamer | 2026-03-30T00:00:00Z
- 链接：https://www.eurogamer.net/kena-bridge-of-spirits-nintendo-switch-2-impressions
- 摘要：After a frustrating drought of native Nintendo Switch 2 ports ( with some special exceptions ) during the console's first six months, reportedly due to the lack of development kits going out to developers, more studios …
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=3, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:regulatory:1; hint:team; high_value_entities:nintendo; game_context; low_information_excerpt; rumor_or_report_sourcing; truncated_article.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D142

- 标题：'I Don't Want to Say They Started Panicking…' — Actor Behind Crimson Desert's Kliff Reveals 'Bridge Point' Where Pearl Abyss Realized the Story and Characters Needed to Change
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-30T00:00:00Z
- 链接：https://www.ign.com/articles/i-dont-want-to-say-they-started-panicking-actor-behind-crimson-deserts-kliff-reveals-bridge-point-where-pearl-abyss-realized-the-story-and-characters-needed-to-change
- 摘要：Alec Newman, the actor who plays Crimson Desert protagonist Kliff, has discussed his work on the game, and revealed how the story and characters changed significantly during development.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D144

- 标题：13 years later, one of the rarest Platinum trophies ever on the PlayStation Vita has finally been earned
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：Eurogamer | 2026-03-30T00:00:00Z
- 链接：https://www.eurogamer.net/one-of-the-rarest-platinum-trophies-ever-has-finally-been-earned
- 摘要：A player has achieved what many had thought impossible, earning one of the most legendary, most elusive Platinum trophies in the history of PlayStation consoles: Ninja Gaiden Sigma 2 's Platinum trophy Master of the Sec…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=3, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:playstation; game_context; low_information_excerpt; truncated_article.
  - Surface cues I would use on a quick pass: technical: ai.

### B2D145

- 标题：A Forgotten Elder Scrolls Game Is Shutting Down Soon
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-30T00:00:00Z
- 链接：https://www.gamespot.com/articles/a-forgotten-elder-scrolls-game-is-shutting-down-soon/1100-6539102/?ftag=CAD-01-10abi2f
- 摘要：One of Bethesda Game Studio's Elder Scrolls spin-offs, The Elder Scrolls: Blades , will be shutting down in June, according to a post on the Nintendo eShop. The free-to-play dungeon crawler and town-builder's last day w…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=0, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:nintendo; game_context; boundary_patterns:1.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D148

- 标题：Get The Complete Castlevania Anime Series On Blu-ray For 26% Off
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-30T00:00:00Z
- 链接：https://www.gamespot.com/articles/get-the-complete-castlevania-anime-series-on-blu-ray-for-26-off/1100-6539100/?ftag=CAD-01-10abi2f
- 摘要：Castlevania fans can now sink their teeth into the entire Netflix anime without breaking the bank. Castlevania: The Complete Series Limited Edition Box Set features all four seasons of the Netflix anime based on Konami'…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=0.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; game_context; noise_patterns:1.
  - Surface cues I would use on a quick pass: regulatory: ban.

### B2D155

- 标题：The Next Piece Of World Of Warcraft Merch Is Nothing You'd Guess
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-30T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-next-piece-of-world-of-warcraft-merch-is-nothing-youd-guess/1100-6539104/?ftag=CAD-01-10abi2f
- 摘要：Blizzard has teamed up with Lodge to create a cast iron skillet themed around World of Warcraft, and it comes with an in-game pet. The 10.25-inch, 5.66-pound skillet features the World of Warcraft logo on the bottom, an…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D156

- 标题：The PS5 Pro Is Still Worth It--For Now
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-30T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-ps5-pro-is-still-worth-it-for-now/1100-6539101/?ftag=CAD-01-10abi2f
- 摘要：Sony announced massive price increases for its PS5 consoles last week, with the PS5 Pro getting slapped with the biggest price hike out of all of them: a whopping $150, pushing the MSRP of the hardware to $900. The good…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=4, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:sony; missing_game_context; announcement_style.
  - Surface cues I would use on a quick pass: market: price.

### B2D159

- 标题：The Biggest New Game Releases Of April 2026
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：GameSpot | 2026-03-31T00:00:00Z
- 链接：https://www.gamespot.com/gallery/the-biggest-new-game-releases-of-april-2026/2900-7623/
- 摘要：Goodbye, first quarter of the 2026 gaming year, hello to the second quarter! We're officially starting the fourth month of the year with a bang, as the month ahead is packed with several highly anticipated releases, int…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:market; game_context.
  - Surface cues I would use on a quick pass: regulatory: ban.

### B2D160

- 标题：The Last Of Us Season 3 Cast: Everyone Who's Coming Back And Joining The Show
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `market`
- 来源：GameSpot | 2026-03-31T00:00:00Z
- 链接：https://www.gamespot.com/gallery/the-last-of-us-season-3-cast-everyone-whos-coming-back-and-joining-the-show/2900-7644/
- 摘要：HBO's popular The Last of Us TV show, based on Naughty Dog's game series, is coming back for its third and possibly final season . Ahead of its expected 2027 premiere, The Last of Us Season 3 is now in production in Can…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `market`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:market; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D162

- 标题：Epic Games CEO Tim Sweeney apologises and seemingly rectifies life insurance situation of laid off worker with terminal brain cancer
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：Eurogamer | 2026-03-31T00:00:00Z
- 链接：https://www.eurogamer.net/epic-games-ceo-tim-sweeney-responds-after-fortnite-layoffs-include-worker-with-brain-cancer
- 摘要：On 24th March, Fortnite developer Epic Games announced mass layoffs that affected over 1,000 workers , including key veterans behind the hit online game. Read more
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=9, noise=6, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:team:2; hint:team; high_value_entities:epic; game_context; low_information_excerpt; short_excerpt; truncated_article; announcement_style; shallow_announcement_penalty; structural_change_keywords.
  - Surface cues I would use on a quick pass: team: layoff, laid off, ceo; technical: ai.

### B2D163

- 标题：New MindsEye Mission Will Reveal 'Evidence' the Game Was 'Sabotaged', Claims CEO
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `team`
- 来源：IGN Game News | 2026-03-31T00:00:00Z
- 链接：https://www.ign.com/articles/new-mindseye-mission-will-reveal-evidence-the-game-was-sabotaged-claims-ceo
- 摘要：Build a Rocket Boy CEO Mark Gerhard says that the studio is preparing to add a new mission to its game, MindsEye, which will include "evidence" supporting his repeated claims that the game was sabotaged by bad actors.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `team`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:team; game_context.
  - Surface cues I would use on a quick pass: team: ceo; technical: ai.

### B2D167

- 标题：Fourth Wing Is Getting the Monopoly Treatment With an Officially Licensed Board Game for Adults Only
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-31T00:00:00Z
- 链接：https://www.ign.com/articles/monopoly-fourth-wing-edition-where-to-buy
- 摘要：Monopoly Fourth Wing Edition is up for preorder at Amazon now with a release date of July 15, 2026. Just like the books themselves, this board game adaptation is meant for adults only with a 17+ age rating.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=2, noise=0, boundary=0.
  - Candidate reasons carried from earlier bucketing: hint:technical; game_context.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D172

- 标题：Microsoft Is Celebrating 25 Years of Xbox by Putting Master Chief on a Fanta Pineapple Can
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：IGN Game News | 2026-03-31T00:00:00Z
- 链接：https://www.ign.com/articles/microsoft-is-celebrating-25-years-of-xbox-by-putting-master-chief-on-a-fanta-pineapple-can
- 摘要：Ever wanted to see Master Chief longingly looking into the horizon from the confines of a carbonated can? Your dream has finally come true.
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=2, boundary=1.
  - Candidate reasons carried from earlier bucketing: hint:technical; high_value_entities:microsoft,xbox,apple; game_context; noise_patterns:1; short_excerpt.
  - Surface cues are weak, which is exactly why this sample needs second-pass human review.

### B2D176

- 标题：The Best PS5 Deals This Week: Save On Consoles, Games, And Accessories - March 31, 2026
- 你的判断：`noise` / `-`
- 当前 draft：`signal` / `technical`
- 来源：GameSpot | 2026-03-31T00:00:00Z
- 链接：https://www.gamespot.com/articles/the-best-ps5-deals-this-week-games-accessories-consoles-and-more/1100-6538557/?ftag=CAD-01-10abi2f
- 摘要：Well, folks, the price hike for PS5 consoles is almost here. On April 2, you'll be paying the highest prices ever for PS5, PS5 Pro, and PS Portal--with PS5 Pro clocking in at a hefty $900. Sony says this is the result o…
- 我为什么暂时没把它降成 noise：
  - I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.
  - Current draft type guess: `technical`. This comes from the existing `expected_signals` annotation in the draft.
  - Heuristic scores: signal=5, noise=0, boundary=2.
  - Candidate reasons carried from earlier bucketing: signal_pattern:market:1; hint:technical; high_value_entities:sony; game_context; boundary_patterns:1.
  - Surface cues I would use on a quick pass: market: price.

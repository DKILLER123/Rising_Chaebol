/**
 * Task T4: Portrait-based image-to-image wardrobe generation for ch110-113.
 *
 * PROVEN WD-12 / 6-a METHOD: feed the character's actual portrait as the base
 * input image into zai.images.generations.edit so the model sees real face
 * pixels (identity preserved: 85-92/100 vs ~25-45 for text-only generation).
 *
 * Usage: bun run scripts/gen-wardrobe-110-113.mjs <job> <stage> [arg]
 *   job   = jiyeon | sohee | jiwon
 *   stage = gen [round] | crop | fixcrops | score | wardrobe | install [variantId]
 *           | final | describe
 *
 * Stages:
 *   gen [round]  generate 6 i2i variants (round 1 = v1..v6, 2 = v7..v12, 3 = v13..v18)
 *   crop         Haar face crops via scripts/wardrobe-crop.py (crop job key = cropJob)
 *   fixcrops     VLM audit of every face crop; VLM-guided face-location re-cropping
 *                for misfires (Haar catching background/hands), exactly as 6-a did
 *   score        3 VLM trials per variant with a detailed forensic identity rubric,
 *                MEDIAN recorded (honest scoring method)
 *   wardrobe     VLM item-by-item verification that EVERY wardrobe item is present
 *   install      strict gate: median >= 80 AND all wardrobe items verified;
 *                `install <variantId>` force-installs a compromise variant (reported honestly)
 *   final        one VLM cross-verification of the installed image vs the base portrait
 *   describe     VLM description of the base portrait (confound awareness)
 *
 * Jobs:
 *   jiyeon: REF=char-parkjiyeon.jpg DEST=wd-jiyeon-athleisure.jpg  (ch110-113)
 *           warm evening apartment entryway, black zip athletic jacket halfway over
 *           dark tee + matching black track pants, lazy low ponytail with escaped
 *           strands, big plastic convenience-store bag of chips + soda (handles
 *           biting fingers), flat house slippers (sneakers on doormat behind),
 *           bright cheerful playful grin
 *   sohee:  REF=char-hansohee.jpg    DEST=wd-sohee-morning.jpg
 *           bright morning living room + sofa; oversized plain white tee like a
 *           mini dress hem mid-thigh, grey sleep shorts barely visible, bare feet,
 *           sleep-mussed hair one side flattened, bare face drowsy half-lidded eyes
 *           with faint pillow crease, calm minimal expression — MODEST & WHOLESOME
 *   jiwon:  REF=char-kimjiwon.jpg    DEST=wd-jiwon-loungewear.jpg
 *           daytime before a modern 20-story apartment tower with green hedges,
 *           blurred convenience store behind; baggy oatmeal-grey loungewear set
 *           (zip hoodie + lounge pants, washed-soft), hair loosely tied back with
 *           temple strands, flat black outdoor slippers, white plastic bag heavy
 *           with snacks + drinks in one hand, smartphone in the other, bare face,
 *           startled mid-glance-up
 */
import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import crypto from 'crypto';

const JOBS = {
  jiyeon: {
    cropJob: 'jiyeon',
    refImg: '/home/z/my-project/epub/OEBPS/images/char-parkjiyeon.jpg',
    outDir: '/home/z/my-project/scripts/wardrobe-jiyeon',
    destImg: '/home/z/my-project/epub/OEBPS/images/wd-jiyeon-athleisure.jpg',
    who: 'Park Ji-yeon',
    prompts: {
      A1: 'Transform this photo of the young woman into a full-body cozy lifestyle editorial: warm evening, she has just stepped through the front door of a modern Seoul apartment, photographed from inside the entryway so the open front door is visible behind her, everything glowing with cozy lamplight. She wears a loose black zip-front athletic jacket thrown casually over a dark tee with the zipper pulled up only halfway, and matching loose black track pants. Her hair is up in one lazy low ponytail with loose strands escaping around her face. One hand grips a large plastic convenience-store bag stuffed full of chip packets and soda bottles, its plastic handles biting into her fingers. On her feet are flat house slippers, with her sneakers sitting on the doormat behind her. She flashes a bright, cheerful, playful grin, mid-greeting energy. Preserve her exact facial identity from the original photo — the same face shape, eyes, nose, lips and skin tone; do not beautify or slim the face. Full body visible from head to slippers.',
      A2: 'Full-body cozy lifestyle photo of the same young woman: a warm evening, she stands in the entryway of a modern Seoul apartment seen from inside, the front door open behind her, cozy lamplight glowing. Outfit: a loose black athletic jacket with a front zipper left halfway up, worn casually open over a dark T-shirt, plus matching loose black track pants. Her hair is pulled into one lazy low ponytail with loose escaped strands framing her face. She carries one large plastic convenience-store shopping bag crammed with chip packets and soda bottles, the handles digging into her fingers. Flat house slippers are on her feet, with her sneakers sitting on the doormat behind her. She wears a bright, cheerful, playful grin as if calling out a greeting. Keep her face exactly identical to the original photo — same eyes, nose, lips, face shape and skin tone. Full body, head to slippers.',
      B1: 'Transform this photo into a warm evening homecoming scene: the young woman stands in the lamp-lit entryway of a modern Seoul apartment, seen from inside the hallway, the open front door behind her. She is dressed in a black zip-up athletic jacket with the zipper at half-mast over a dark tee, with loose matching black track pants below. Her hair is in a single low, lazy ponytail with a few strands escaping at the sides. In one hand she hauls a big plastic convenience-store bag, visibly packed with chip packets and soda bottles, the handles cutting into her fingers. Her feet are in flat house slippers, and on the doormat behind her lie her sneakers. She is caught mid-greeting with a bright, playful, cheerful grin. Her face must stay true to the original photo: same facial proportions, features and skin tone, no beautification. Full-body editorial photo in warm evening light.',
      B2: 'Cozy warm-evening editorial, full body: the same young woman arriving home at a modern Seoul apartment — camera inside the entryway looking toward her, the front door open behind her, soft lamplight. She wears a loose black zip-front sports jacket unzipped to halfway over a dark top and matching loose black track pants. Her hair sits in one lazy low ponytail with flyaway strands escaping. A large plastic convenience-store bag, stuffed with chip packets and soda bottles, hangs from one hand, the handles biting her fingers. Flat house slippers on her feet; her sneakers rest on the doormat behind her. She greets us with a bright, cheerful, playful grin, mid-greeting energy. Preserve the exact face of the original photo — identical eyes, nose, lips, jawline and skin tone.',
      C1: 'Dress the same young woman as if she has just gotten home on a warm evening: modern Seoul apartment entryway seen from inside, front door open behind her, cozy lamplight. Loose black zip-up athletic jacket over a dark tee with the zipper halfway; matching loose black track pants; hair in one lazy low ponytail with escaped loose strands; a big plastic convenience-store bag packed with chip packets and soda bottles gripped in one hand, handles biting her fingers; flat house slippers on her feet with sneakers visible on the doormat behind her; bright cheerful playful grin, mid-greeting energy. Keep her face identical to the original image. Full-body lifestyle photo, warm evening tones.',
      C2: 'Reimagine this photo as a full-body warm homecoming snapshot: the young woman in the entryway of a modern Seoul apartment at warm dusk, viewed from inside with the open front door behind her and cozy lamplight washing the scene. Wardrobe and props: a loose black athletic zip jacket worn open-to-halfway over a dark tee, matching loose black track pants, hair up in one lazy low ponytail with loose strands escaping, one large plastic convenience-store bag stuffed with chip packets and soda bottles held by its handles with the plastic biting into her fingers, flat house slippers on her feet, and her sneakers sitting on the doormat behind her. Expression: a bright, cheerful, playful grin — mid-greeting energy. Same face as the original photo, unchanged: eyes, nose, lips and skin tone. Full body from head to toe.'
    },
    reinforce: ' IMPORTANT — every one of these details must be clearly visible in the image: the black jacket has a FRONT ZIPPER stopped at roughly halfway over a dark tee; the black track pants match the jacket; the hair is ONE low ponytail with loose escaped strands; the plastic convenience-store bag is clearly stuffed with chip packets AND soda bottles and its handles bite into her fingers; she wears flat house slippers while her SNEAKERS sit on the doormat behind her; her expression is a bright cheerful playful grin; the setting is a warm-evening apartment entryway seen from inside with the front door open behind her and cozy lamplight.',
    wardrobeItems: ['jacketHalfZip', 'trackPants', 'lowPonytail', 'cvsBagChipsSoda', 'houseSlippers', 'sneakersDoormat', 'brightGrin', 'entrywayScene'],
    wardrobeAsk: 'Examine this image very carefully and answer ONLY with a numbered list. For each question reply exactly "N. YES — <short reason>" or "N. NO — <what is actually there>". (1) Is she wearing a loose black zip-front athletic jacket over a dark tee, with the front zipper stopped at roughly halfway? (2) Is she wearing matching loose black track pants? (3) Is her hair in ONE low ponytail with loose escaped strands? (4) Is she holding a large plastic convenience-store bag that is visibly stuffed with chip packets AND soda bottles, with the handles around her fingers? (5) Is she wearing flat house slippers on her feet? (6) Are sneakers visible on the doormat or floor behind her? (7) Is her expression a bright, cheerful, playful grin with mid-greeting energy? (8) Is the setting a warm-evening apartment entryway seen from inside, with the front door open behind her and cozy lamplight?'
  },
  sohee: {
    cropJob: 'sohee-morning',
    refImg: '/home/z/my-project/epub/OEBPS/images/char-hansohee.jpg',
    outDir: '/home/z/my-project/scripts/wardrobe-sohee-morning',
    destImg: '/home/z/my-project/epub/OEBPS/images/wd-sohee-morning.jpg',
    who: 'Han So-hee',
    prompts: {
      A1: 'Transform this photo of the young woman into a full-body wholesome morning-life editorial: bright morning sunlight fills a modern living room, a sofa behind her. She has just woken up and wears one oversized plain white T-shirt worn like a mini dress, its hem at mid-thigh, with grey sleep shorts just barely visible beneath the hem. She is totally barefoot. Her long dark hair is sleep-mussed and unbrushed, one side flattened from the pillow. Her face is completely bare with no makeup, eyes drowsy and half-lidded, a faint pillow crease on one cheek, and a calm, minimal expression. The image is fully modest and wholesome — she is simply a sleepy girl in a big shirt, covered from shoulders to mid-thigh. Preserve her exact facial identity from the original photo — same face shape, eyes, nose, lips, the small mole under her eye, and skin tone; do not beautify or add makeup. Full body visible from head to bare feet, family-magazine morning lifestyle style.',
      A2: 'Full-body morning lifestyle photo of the same young woman: bright natural sunlight streams into a modern living room with a sofa behind her. She has just rolled out of bed wearing a single oversized plain white T-shirt like a mini dress, the hem ending at mid-thigh, grey sleep shorts only barely peeking out beneath that hem. Her feet are totally bare. Her long dark hair is unbrushed and sleep-mussed, one side flattened. She has a completely bare face — zero makeup — with drowsy half-lidded eyes, a faint pillow crease visible on one cheek, and a calm, minimal, just-awake expression. Fully modest and wholesome: covered from shoulders to mid-thigh by the big tee. Keep her face exactly identical to the original photo, including the small mole under her eye; do not beautify. Full body from head to bare feet.',
      B1: 'Transform this photo into a serene just-woken-up scene: the young woman stands in a bright modern living room flooded with morning sunlight, a sofa visible behind her. She wears one oversized plain white T-shirt as a mini dress with the hem at mid-thigh; grey sleep shorts are just barely visible beneath the hem. She is completely barefoot. Her long dark hair is sleep-mussed and unbrushed, flattened on one side. Her bare face shows no makeup at all — drowsy half-lidded eyes, a faint pillow crease on one cheek, calm minimal expression. Modest and wholesome framing: she is covered from shoulders to mid-thigh by the tee; a sleepy girl in a big shirt, nothing more. Her face must stay true to the original photo — same eyes, nose, lips, face shape, the small mole under her eye, same skin tone. Full-body morning editorial, head to bare feet.',
      B2: 'Bright-morning editorial, full body, wholesome family-magazine style: the same young woman just after waking, standing in a sunlit modern living room with a sofa behind her. Wardrobe: one oversized plain white T-shirt worn like a mini dress, hem at mid-thigh, with grey sleep shorts barely visible below the hem — she is totally barefoot. Her long dark hair is sleep-mussed, unbrushed, one side visibly flattened. Face: completely bare with zero makeup, drowsy half-lidded eyes, a faint pillow crease on one cheek, calm minimal expression. Fully modest — covered from shoulders to mid-thigh. Preserve the exact face of the original photo: identical eyes, nose, lips, jawline, the small mole under her eye, and skin tone; no beautification, no makeup.',
      C1: 'Dress the same young woman as a sleepy girl in a big shirt on a bright morning: modern living room in strong natural sunlight, sofa behind her. One oversized plain white T-shirt worn like a mini dress with the hem at mid-thigh; grey sleep shorts just barely visible beneath the hem; totally bare feet; long dark hair sleep-mussed and unbrushed with one side flattened; completely bare face with no makeup, drowsy half-lidded eyes, a faint pillow crease on one cheek; calm minimal expression. Modest and wholesome — fully covered from shoulders to mid-thigh by the tee. Keep her face identical to the original image, including the small mole under her eye. Full-body morning lifestyle photo.',
      C2: 'Reimagine this photo as a full-body morning-after-waking snapshot: the young woman standing in a bright modern living room, morning sunlight pouring in, a sofa behind her. She wears a single oversized plain white T-shirt like a mini dress, hem at mid-thigh, with grey sleep shorts just barely visible under the hem, and nothing on her totally bare feet. Her long dark hair is sleep-mussed and unbrushed, one side flattened from the pillow. Her face is bare with zero makeup — drowsy half-lidded eyes, faint pillow crease on one cheek, calm minimal expression. Wholesome and fully modest, covered shoulders to mid-thigh. Same face as the original photo, unchanged: eyes, nose, lips, the small mole under her eye, skin tone. Full body head to bare feet.'
    },
    reinforce: ' IMPORTANT — every one of these details must be clearly visible: the oversized plain WHITE T-shirt is worn like a mini dress with the hem at mid-thigh; GREY sleep shorts are just barely visible beneath that hem; her feet are totally BARE; her long dark hair is sleep-mussed, unbrushed, with one side flattened; her face has ZERO makeup with drowsy half-lidded eyes and a faint pillow crease on one cheek; her expression is calm and minimal; the scene is a bright morning modern living room with a sofa behind her. Keep it fully modest and wholesome — covered from shoulders to mid-thigh.',
    wardrobeItems: ['oversizedWhiteTee', 'greySleepShorts', 'bareFeet', 'sleepMussedHair', 'bareFaceDrowsy', 'pillowCrease', 'calmExpression', 'morningLivingRoom', 'modestSafe'],
    wardrobeAsk: 'Examine this image very carefully and answer ONLY with a numbered list. For each question reply exactly "N. YES — <short reason>" or "N. NO — <what is actually there>". (1) Is she wearing an oversized plain white T-shirt like a mini dress, with the hem at mid-thigh? (2) Are grey sleep shorts just barely visible beneath the hem? (3) Are her feet totally bare — no socks, no shoes? (4) Is her long dark hair sleep-mussed and unbrushed, with one side flattened? (5) Is her face completely bare with no makeup, with drowsy half-lidded eyes? (6) Is there a faint pillow crease visible on one cheek? (7) Is her expression calm and minimal? (8) Is the setting a bright morning modern living room with a sofa behind her? (9) Is she fully modest — covered from shoulders to mid-thigh by the tee, with nothing suggestive or revealing anywhere in the image?'
  },
  jiwon: {
    cropJob: 'jiwon',
    refImg: '/home/z/my-project/epub/OEBPS/images/char-kimjiwon.jpg',
    outDir: '/home/z/my-project/scripts/wardrobe-jiwon',
    destImg: '/home/z/my-project/epub/OEBPS/images/wd-jiwon-loungewear.jpg',
    who: 'Kim Ji-won',
    prompts: {
      A1: 'Transform this photo of the young woman into a full-body candid editorial, daytime: she stands outdoors in front of a modern apartment tower about twenty stories tall with tidy green hedges at its base, a convenience-store storefront softly blurred in the background. She wears a baggy oatmeal-grey home loungewear two-piece — a soft zip-up hoodie and matching lounge pants, washed-soft and well-worn. Her hair is loosely tied back with strands escaping at the temples. On her feet are flat black outdoor slippers. In one hand she carries a white plastic bag heavy with snack boxes and drink bottles; in the other hand she holds a smartphone. Her face is bare with zero makeup, and her eyes are startled, caught mid-glance-up as if surprised off guard. Preserve her exact facial identity — same face shape, eyes, nose, lips and skin tone as the original photo; do not beautify. Candid Korean neighborhood daylight photo, full body visible head to slippers.',
      A2: 'Full-body candid daytime photo of the same young woman: she is outside a modern high-rise apartment complex — a tower of roughly twenty stories with neat green hedges along its base — with a blurred convenience-store storefront in the background. She is dressed down in a baggy oatmeal-grey loungewear set: a soft zip-front hoodie with matching lounge pants, both looking washed-soft and lived-in. Her hair is loosely tied back, strands escaping at her temples. Her feet are in flat black outdoor slippers. One hand holds a white plastic bag loaded heavy with snack boxes and drink bottles; the other hand holds her smartphone up. Bare face, zero makeup, eyes startled in a mid-glance-up moment as if caught off guard by the camera. Keep her face exactly identical to the original photo — same eyes, nose, lips, face shape and skin tone. Full body head to slippers.',
      B1: 'Transform this photo into a candid caught-off-guard moment: daytime, the young woman stands in front of a modern twenty-story apartment tower framed by tidy green hedges, a convenience store softly blurred behind her. She wears baggy oatmeal-grey home loungewear — a soft zip-up hoodie and matching lounge pants with a washed-soft, well-worn look. Her hair is loosely tied back with loose strands escaping at the temples. Flat black outdoor slippers are on her feet. In one hand hangs a white plastic bag heavy with snack boxes and drink bottles; her other hand holds a smartphone. Her bare face wears zero makeup, and her startled eyes are caught mid-glance-up toward the camera, as if surprised. Her face must stay true to the original photo: same facial proportions, features and skin tone, no beautification. Full-body candid daylight editorial.',
      B2: 'Candid neighborhood daylight editorial, full body: the same young woman caught just outside her modern apartment complex — a tall tower of about twenty stories with tidy green hedges at its base, and a softly blurred convenience-store storefront behind her. Outfit: a baggy oatmeal-grey loungewear two-piece, soft zip hoodie plus matching lounge pants, washed-soft and comfortable. Hair loosely tied back with escaping strands at the temples. Flat black outdoor slippers on her feet. One hand carries a white plastic bag visibly heavy with snack boxes and drink bottles; the other hand holds a smartphone. Bare face with zero makeup; eyes startled, mid-glance-up, caught off guard. Preserve the exact face of the original photo — identical eyes, nose, lips, jawline and skin tone.',
      C1: 'Dress the same young woman in lazy daytime errand clothes: she stands before a modern apartment tower around twenty stories tall with tidy green hedges, a convenience store softly blurred behind her. Baggy oatmeal-grey home loungewear two-piece — soft zip hoodie and matching lounge pants, washed-soft; hair loosely tied back with strands escaping at the temples; flat black outdoor slippers; one white plastic bag heavy with snack boxes and drink bottles in one hand; smartphone in the other hand; bare face with zero makeup; eyes startled mid-glance-up as if caught off guard. Keep her face identical to the original image. Full-body candid daylight photo.',
      C2: 'Reimagine this photo as a full-body caught-off-guard snapshot: the young woman outside on a daytime errand run in front of her modern high-rise apartment building — about twenty stories, tidy green hedges at the base — with a convenience-store storefront softly blurred in the background behind her. She wears a baggy oatmeal-grey loungewear set (soft zip-up hoodie + matching lounge pants, washed-soft and lived-in), hair loosely tied back with temple strands escaping, flat black outdoor slippers on her feet. In one hand: a white plastic bag heavy with snack boxes and drink bottles. In the other: her smartphone. Her face is bare with zero makeup and her eyes are startled, mid-glance-up, as if surprised off guard. Same face as the original photo, unchanged: eyes, nose, lips and skin tone. Full body head to slippers.'
    },
    reinforce: ' IMPORTANT — every one of these details must be clearly visible: the loungewear is a baggy OATMEAL-GREY two-piece (soft zip hoodie + matching lounge pants) with a washed-soft look; her hair is loosely tied back with strands escaping at the temples; her footwear is flat BLACK outdoor slippers; she holds ONE white plastic bag clearly heavy with snack boxes AND drink bottles in one hand and a SMARTPHONE in the other hand; her face is bare with zero makeup; her eyes look startled, mid-glance-up, caught off guard; the setting is daytime in front of a modern ~20-story apartment tower with tidy green hedges and a softly blurred convenience store behind her.',
    wardrobeItems: ['oatmealLoungewear', 'hairTiedBackTemples', 'blackSlippers', 'whiteBagSnacks', 'smartphone', 'bareFace', 'startledGlanceUp', 'aptTowerScene'],
    wardrobeAsk: 'Examine this image very carefully and answer ONLY with a numbered list. For each question reply exactly "N. YES — <short reason>" or "N. NO — <what is actually there>". (1) Is she wearing a baggy oatmeal-grey home loungewear two-piece — a soft zip-up hoodie with matching lounge pants — with a washed-soft look? (2) Is her hair loosely tied back with strands escaping at the temples? (3) Is she wearing flat black outdoor slippers? (4) Is she holding ONE white plastic bag that is visibly heavy with snack boxes and drink bottles? (5) Is she holding a smartphone in her other hand? (6) Is her face bare with zero makeup? (7) Are her eyes startled, caught mid-glance-up as if off guard? (8) Is the setting daytime in front of a modern high-rise apartment tower (around twenty stories) with tidy green hedges, and a convenience store softly blurred behind her?'
  }
};

const SIZE = '864x1152';
const PROMPT_KEYS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
const FACE_MIN_STRICT = 80;   // strict winner threshold (per task spec)
const WARDROBE_MIN = 70;      // wardrobe-check eligibility (compromise visibility)

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const md5 = (p) => crypto.createHash('md5').update(fs.readFileSync(p)).digest('hex');

function roundIds(round) {
  const start = (round - 1) * 6 + 1;
  return Array.from({ length: 6 }, (_, i) => `v${start + i}`);
}
function allIds() {
  return Array.from({ length: 18 }, (_, i) => `v${i + 1}`);
}
function promptFor(job, round, idx) {
  const key = PROMPT_KEYS[idx];
  let p = job.prompts[key];
  if (round > 1) p += job.reinforce;
  return { key, prompt: p };
}

async function vlmChat(zai, text, b64List, retries = 5) {
  const content = [{ type: 'text', text }];
  for (const b64 of b64List) {
    content.push({ type: 'image_url', image_url: { url: `data:image/jpeg;base64,${b64}` } });
  }
  for (let a = 1; a <= retries; a++) {
    try {
      const res = await zai.chat.completions.createVision({
        messages: [{ role: 'user', content }],
        thinking: { type: 'enabled' }
      });
      return res.choices[0]?.message?.content || '';
    } catch (e) {
      const is429 = /429|too many/i.test(String(e?.message || e));
      console.error(`  vlm attempt ${a} failed: ${(e?.message || e).toString().slice(0, 120)}`);
      if (a < retries) await sleep(is429 ? 25000 * a : 5000 * a);
    }
  }
  return '';
}

async function generateVariant(zai, job, id, prompt, promptKey) {
  const outPath = path.join(job.outDir, `${id}.jpg`);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 10000) {
    console.log(`${id}: exists (${fs.statSync(outPath).size} bytes), skipping`);
    return true;
  }
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const dataUrl = `data:image/jpeg;base64,${fs.readFileSync(job.refImg).toString('base64')}`;
      const response = await zai.images.generations.edit({
        prompt,
        images: [{ url: dataUrl }],
        size: SIZE
      });
      const b64 = response?.data?.[0]?.base64;
      if (!b64) throw new Error('no image data in response');
      const buf = Buffer.from(b64, 'base64');
      fs.writeFileSync(outPath, buf);
      console.log(`${id} (prompt ${promptKey}, attempt ${attempt}): saved ${outPath} (${buf.length} bytes)`);
      return true;
    } catch (e) {
      console.error(`${id} (prompt ${promptKey}) attempt ${attempt} failed: ${e?.message || e}`);
      if (attempt < 3) await sleep(8000 * attempt);
    }
  }
  console.error(`${id}: FAILED after 3 attempts`);
  return false;
}

function parseCropAudit(txt) {
  const m = (txt || '').trim().match(/^\s*(yes|no)\b/i);
  if (m) return m[1].toLowerCase() === 'yes';
  return /\byes\b/i.test(txt || '') && !/\bno\b/i.test(txt || '') ? true : null;
}

function parseLocate(txt) {
  const m = (txt || '').match(/cx\s*=\s*(\d+(?:\.\d+)?)\s*%\s*[,;]?\s*cy\s*=\s*(\d+(?:\.\d+)?)\s*%\s*[,;]?\s*(?:size|w|width)\s*=\s*(\d+(?:\.\d+)?)\s*%/i);
  if (!m) return null;
  return { cx: parseFloat(m[1]), cy: parseFloat(m[2]), size: parseFloat(m[3]) };
}

const RUBRIC = (who) => `You are a strict forensic face-identity examiner comparing two face crops. Image 1 is the reference face of ${who}. Image 2 is a candidate face crop taken from a different photograph that claims to show the same person. Examine these features one by one and note matches and mismatches briefly: overall face shape and jawline; cheekbones; eye shape, eyelids and eye spacing; eyebrow shape and thickness; nose bridge and nose tip; lip shape and cupid's bow; chin; skin tone and texture; any distinctive marks such as moles or beauty marks. Then give ONE overall integer score 0-100 for same-person facial identity using this scale: 90-100 = almost certainly the same person; 80-89 = same person with minor differences; 70-79 = probably the same person, soft evidence; 50-69 = uncertain; 0-49 = likely a different person. Ignore hairstyle, headwear, makeup, lighting and facial expression where they do not change the underlying bone structure. End your reply with exactly one line: "SCORE: NN".`;

function parseScore(txt) {
  const m = (txt || '').match(/SCORE:\s*(\d{1,3})/i);
  if (m) { const n = parseInt(m[1], 10); if (n <= 100) return n; }
  const nums = (txt || '').match(/(\d{1,3})/g);
  if (nums) { const n = parseInt(nums[nums.length - 1], 10); if (n <= 100) return n; }
  return null;
}

function parseWardrobe(txt, nItems) {
  const map = {};
  const re = /\(?\s*(\d{1,2})\s*[).:\]-]*\s*(yes|no)\b/gi;
  let m;
  while ((m = re.exec(txt))) {
    const n = parseInt(m[1], 10);
    if (!(n in map)) map[n] = m[2].toLowerCase() === 'yes';
  }
  const complete = Array.from({ length: nItems }, (_, i) => i + 1).every(n => n in map);
  return { map, complete };
}

function wardrobeAllYes(map, nItems) {
  return Array.from({ length: nItems }, (_, i) => i + 1).every(n => map[n] === true);
}

function loadResults(job) {
  const p = path.join(job.outDir, 'results.json');
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')) : {};
}
function saveResults(job, results) {
  fs.writeFileSync(path.join(job.outDir, 'results.json'), JSON.stringify(results, null, 2));
}

async function stageDescribe(zai, job) {
  const b64 = fs.readFileSync(job.refImg).toString('base64');
  const txt = await vlmChat(zai, `Describe this portrait of a young Korean woman for an identity-reference file: hair style and color, any headwear or accessories, visible clothing, facial features (face shape, eyes, nose, lips), distinctive marks (moles etc.), expression, and framing. Short factual list.`, [b64]);
  console.log(`--- ${job.who} base portrait description ---\n${txt.trim()}`);
  const results = loadResults(job);
  results.portraitDescription = txt.trim();
  saveResults(job, results);
}

async function stageFixCrops(zai, job) {
  console.log('\n--- VLM audit of face crops (is each a usable face close-up?) ---');
  const faceDir = path.join(job.outDir, 'faces');
  const results = loadResults(job);
  const boxes = {};
  let changed = false;
  for (const id of [...allIds(), 'ref']) {
    const cropPath = path.join(faceDir, `${id}.jpg`);
    if (!fs.existsSync(cropPath)) continue;
    if (results[id]?.cropAudit === 'yes') { console.log(`${id}: already audited OK`); continue; }
    const b64 = fs.readFileSync(cropPath).toString('base64');
    const txt = await vlmChat(zai, 'Does this image contain one human face that fills a good portion of the frame — a usable face close-up crop — rather than only background, hands, or objects? Answer YES or NO first, then one short sentence.', [b64]);
    const verdict = parseCropAudit(txt);
    console.log(`${id}: ${verdict === true ? 'OK' : verdict === false ? 'MISFIRE' : 'UNPARSEABLE'} — ${txt.trim().split('\n')[0].slice(0, 120)}`);
    if (verdict === true) {
      results[id] = { ...(results[id] || {}), cropAudit: 'yes' };
    } else if (verdict === false) {
      // VLM-guided face-location re-crop (6-a method)
      const fullB64 = id === 'ref'
        ? fs.readFileSync(job.refImg).toString('base64')
        : fs.readFileSync(path.join(job.outDir, `${id}.jpg`)).toString('base64');
      let loc = null;
      let locTxt = '';
      for (let a = 1; a <= 2 && !loc; a++) {
        locTxt = await vlmChat(zai, id === 'ref'
          ? 'Estimate the location of the woman\'s face in this portrait photo. Reply in exactly this format and nothing else: cx=NN% cy=NN% size=NN% — where cx and cy are the face-center position as percentages of image width and height, and size is the face width as a percentage of image width.'
          : 'Estimate the location of the woman\'s face in this full photograph (she may be small in the frame). Reply in exactly this format and nothing else: cx=NN% cy=NN% size=NN% — where cx and cy are the face-center position as percentages of image width and height, and size is the face width as a percentage of image width.', [fullB64]);
        loc = parseLocate(locTxt);
      }
      if (loc) {
        const imgW = 864, imgH = 1152;
        const w = Math.max(30, Math.round(loc.size / 100 * imgW));
        const cx = loc.cx / 100 * imgW, cy = loc.cy / 100 * imgH;
        const x = Math.max(0, Math.round(cx - w / 2));
        const y = Math.max(0, Math.round(cy - w / 2));
        boxes[id] = [x, y, w, w];
        results[id] = { ...(results[id] || {}), cropAudit: 'recrop-pending', vlmBox: [x, y, w, w], vlmLocate: locTxt.trim().slice(0, 80) };
        changed = true;
        console.log(`  ${id}: VLM-guided box ${[x, y, w, w]}`);
      } else {
        results[id] = { ...(results[id] || {}), cropAudit: 'unparseable', cropAuditRaw: txt.trim().slice(0, 200) };
      }
    } else {
      results[id] = { ...(results[id] || {}), cropAudit: 'unparseable', cropAuditRaw: txt.trim().slice(0, 200) };
    }
    saveResults(job, results);
    await sleep(600);
  }
  if (changed || Object.values(results).some(r => r?.cropAudit === 'recrop-pending') || Object.keys(boxes).length) {
    // merge any previously stored pending boxes
    for (const id of [...allIds(), 'ref']) {
      if (results[id]?.cropAudit === 'recrop-pending' && results[id]?.vlmBox && !boxes[id]) boxes[id] = results[id].vlmBox;
    }
    const boxesPath = path.join(job.outDir, 'boxes.json');
    fs.writeFileSync(boxesPath, JSON.stringify(boxes, null, 2));
    console.log(`re-cropping with VLM-guided boxes: ${JSON.stringify(boxes)}`);
    execFileSync('python3', ['/home/z/my-project/scripts/wardrobe-crop.py', job.cropJob, '--boxes', boxesPath], { stdio: 'inherit' });
    // re-audit the re-cropped ones once
    for (const id of Object.keys(boxes)) {
      const b64 = fs.readFileSync(path.join(faceDir, `${id}.jpg`)).toString('base64');
      const txt = await vlmChat(zai, 'Does this image contain one human face that fills a good portion of the frame — a usable face close-up crop — rather than only background, hands, or objects? Answer YES or NO first, then one short sentence.', [b64]);
      const verdict = parseCropAudit(txt);
      results[id] = { ...(results[id] || {}), cropAudit: verdict === true ? 'recropped-ok' : verdict === false ? 'recrop-still-bad' : 'unparseable', recropAudit: txt.trim().slice(0, 120) };
      console.log(`  re-audit ${id}: ${results[id].cropAudit} — ${txt.trim().split('\n')[0].slice(0, 100)}`);
      saveResults(job, results);
      await sleep(600);
    }
  }
  saveResults(job, results);
  return results;
}

async function stageScore(zai, job) {
  console.log('\n--- VLM face-crop scoring: 3 trials per variant, MEDIAN (forensic rubric) ---');
  const faceDir = path.join(job.outDir, 'faces');
  const refB64 = fs.readFileSync(path.join(faceDir, 'ref.jpg')).toString('base64');
  const results = loadResults(job);
  for (const id of allIds()) {
    const cropPath = path.join(faceDir, `${id}.jpg`);
    if (!fs.existsSync(cropPath)) continue;
    const audit = results[id]?.cropAudit;
    if (audit && audit !== 'yes' && audit !== 'recropped-ok') {
      console.log(`${id}: crop audit '${audit}' — not a usable face crop, disqualified from scoring`);
      continue;
    }
    if (results[id]?.faceScores?.length === 3) { console.log(`${id}: already scored (median ${results[id].faceMedian})`); continue; }
    const candB64 = fs.readFileSync(cropPath).toString('base64');
    const scores = [];
    const notes = [];
    for (let t = 1; t <= 3; t++) {
      const txt = await vlmChat(zai, RUBRIC(job.who), [refB64, candB64]);
      const s = parseScore(txt);
      if (s !== null) { scores.push(s); notes.push(`t${t}: ${s} — ${(txt || '').trim().split('\n').filter(l => !/^SCORE:/i.test(l)).join(' ').slice(0, 200)}`); }
      await sleep(800);
    }
    const sorted = [...scores].sort((a, b) => a - b);
    const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
    results[id] = { ...(results[id] || {}), faceScores: scores, faceMedian: median, faceNotes: notes };
    console.log(`${id}: scores [${scores.join(', ')}] -> median ${median}`);
    saveResults(job, results);
  }
  return results;
}

async function stageWardrobe(zai, job) {
  console.log(`\n--- VLM wardrobe verification, item by item (variants with median >= ${WARDROBE_MIN}) ---`);
  const results = loadResults(job);
  const n = job.wardrobeItems.length;
  for (const id of allIds()) {
    const r = results[id];
    if (!r || r.faceMedian === null || r.faceMedian === undefined || r.faceMedian < WARDROBE_MIN) {
      if (r?.faceMedian !== undefined) console.log(`${id}: median ${r?.faceMedian} < ${WARDROBE_MIN}, skip wardrobe check`);
      continue;
    }
    if (r.wardrobeChecked) { console.log(`${id}: wardrobe already checked (${r.wardrobeYesCount}/${n} yes)`); continue; }
    const b64 = fs.readFileSync(path.join(job.outDir, `${id}.jpg`)).toString('base64');
    let parsed = { map: {}, complete: false };
    let txt = '';
    for (let a = 1; a <= 2; a++) {
      txt = await vlmChat(zai, job.wardrobeAsk, [b64]);
      parsed = parseWardrobe(txt, n);
      if (parsed.complete) break;
      await sleep(1000);
    }
    const yesCount = Object.values(parsed.map).filter(Boolean).length;
    const failed = Array.from({ length: n }, (_, i) => i + 1).filter(k => parsed.map[k] !== true).map(k => `${k}:${job.wardrobeItems[k - 1]}`);
    results[id] = { ...r, wardrobeChecked: true, wardrobeMap: parsed.map, wardrobeComplete: parsed.complete, wardrobeAllYes: parsed.complete && wardrobeAllYes(parsed.map, n), wardrobeYesCount: yesCount, wardrobeFailedItems: failed, wardrobeRaw: (txt || '').trim().slice(0, 1200) };
    console.log(`${id}: ${yesCount}/${n} items YES${parsed.complete ? '' : ' (PARSE INCOMPLETE)'}${failed.length ? ' failed: ' + failed.join(', ') : ' — ALL PASS'}`);
    saveResults(job, results);
    await sleep(800);
  }
  return results;
}

function eligibleStrict(job, results) {
  const n = job.wardrobeItems.length;
  const out = [];
  for (const id of allIds()) {
    const r = results[id];
    if (!r || r.faceMedian === null || r.faceMedian === undefined) continue;
    const audit = r.cropAudit;
    if (audit && audit !== 'yes' && audit !== 'recropped-ok') continue;
    if (r.faceMedian < FACE_MIN_STRICT) continue;
    if (!r.wardrobeAllYes) continue;
    out.push({ id, median: r.faceMedian, items: r.wardrobeYesCount ?? n });
  }
  out.sort((a, b) => b.median - a.median || b.items - a.items);
  return out;
}

function bestCompromise(job, results) {
  const n = job.wardrobeItems.length;
  let best = null;
  for (const id of allIds()) {
    const r = results[id];
    if (!r || r.faceMedian === null || r.faceMedian === undefined) continue;
    const audit = r.cropAudit;
    if (audit && audit !== 'yes' && audit !== 'recropped-ok') continue;
    const items = r.wardrobeYesCount ?? -1;
    const cand = { id, median: r.faceMedian, items };
    if (!best) { best = cand; continue; }
    if (items > best.items || (items === best.items && cand.median > best.median)) best = cand;
  }
  return best;
}

async function stageInstall(job, results, forcedId) {
  console.log('\n--- Decision ---');
  let winner = null;
  let compromise = false;
  if (forcedId) {
    const r = results[forcedId];
    if (!r) { console.log(`forced variant ${forcedId} not found in results`); process.exit(1); }
    winner = { id: forcedId, median: r.faceMedian, items: r.wardrobeYesCount ?? '?' };
    compromise = !(r.faceMedian >= FACE_MIN_STRICT && r.wardrobeAllYes);
    console.log(`FORCED INSTALL ${forcedId} (median ${r.faceMedian}, wardrobe ${r.wardrobeYesCount}/${job.wardrobeItems.length}${compromise ? ' — COMPROMISE, below strict gate' : ''})`);
  } else {
    const eligible = eligibleStrict(job, results);
    console.log(`Strict-eligible (median>=${FACE_MIN_STRICT} AND all ${job.wardrobeItems.length} wardrobe items verified):`);
    for (const e of eligible) console.log(`  ${e.id}: median ${e.median}, items ${e.items}/${job.wardrobeItems.length}`);
    if (eligible.length === 0) {
      console.log('NO STRICT WINNER — nothing installed automatically.');
      const best = bestCompromise(job, results);
      if (best) console.log(`Best available fallback (NOT installed): ${best.id} median ${best.median}, items ${best.items}/${job.wardrobeItems.length} — run 'install ${best.id}' to force a compromise install.`);
      results.decision = { installed: false, reason: 'no variant reached median>=80 + all wardrobe items' };
      saveResults(job, results);
      return;
    }
    winner = eligible[0];
    console.log(`Strict winner: ${winner.id} (median ${winner.median})`);
  }
  const src = path.join(job.outDir, `${winner.id}.jpg`);
  fs.copyFileSync(src, job.destImg);
  const pubDest = path.join('/home/z/my-project/public/book', path.basename(job.destImg));
  fs.copyFileSync(src, pubDest);
  const s1 = fs.statSync(job.destImg).size, s2 = fs.statSync(pubDest).size;
  const m0 = md5(src), m1 = md5(job.destImg), m2 = md5(pubDest);
  const ok = m0 === m1 && m1 === m2;
  console.log(`INSTALLED ${src} ->\n  ${job.destImg} (${s1} bytes, md5 ${m1})\n  ${pubDest} (${s2} bytes, md5 ${m2})\n  md5-verified byte-identical: ${ok ? 'PASS' : 'FAIL'} [variant ${winner.id}, median face score ${winner.median}${compromise ? ', COMPROMISE' : ''}]`);
  results.decision = { installed: true, variant: winner.id, median: winner.median, compromise, bytes: s1, md5: m1, md5Pub: m2 };
  saveResults(job, results);
}

async function stageFinal(zai, job) {
  console.log('\n--- Final cross-verification: installed image vs base portrait ---');
  const results = loadResults(job);
  if (!results.decision?.installed) { console.log('nothing installed yet'); return; }
  const refB64 = fs.readFileSync(job.refImg).toString('base64');
  const instB64 = fs.readFileSync(job.destImg).toString('base64');
  const checklist = job.wardrobeAsk.replace(/^.*?\(1\)/s, '(1)').replace(/Answer ONLY with a numbered list\.\s*/i, '');
  const txt = await vlmChat(zai, `Image 1 is the reference portrait of ${job.who}. Image 2 is a full-length photo generated from that portrait in a different outfit and setting. (A) Score the facial-identity match between the two images 0-100 (90-100 almost certainly the same person; 80-89 same person with minor differences; 70-79 probably the same person; 50-69 uncertain; 0-49 different person). (B) Then verify this checklist against image 2: ${checklist} Answer as: "IDENTITY: NN" followed by "CHECKLIST:" and your numbered YES/NO list with brief reasons.`, [refB64, instB64]);
  const idm = txt.match(/IDENTITY:\s*(\d{1,3})/i);
  const identity = idm ? parseInt(idm[1], 10) : null;
  console.log(txt.trim());
  results.finalVerification = { identity, raw: txt.trim().slice(0, 2000), installedMd5: md5(job.destImg) };
  saveResults(job, results);
  console.log(`\nFINAL identity score: ${identity}/100`);
}

async function main() {
  const jobKey = process.argv[2];
  const stage = process.argv[3] || 'gen';
  const arg = process.argv[4];
  if (!JOBS[jobKey]) {
    console.error('usage: bun run scripts/gen-wardrobe-110-113.mjs <jiyeon|sohee|jiwon> <gen|crop|fixcrops|score|wardrobe|install|final|describe> [round|variantId]');
    process.exit(1);
  }
  const job = JOBS[jobKey];
  fs.mkdirSync(job.outDir, { recursive: true });
  fs.mkdirSync(path.join(job.outDir, 'faces'), { recursive: true });
  const zai = await ZAI.create();

  if (stage === 'describe') {
    await stageDescribe(zai, job);
  } else if (stage === 'gen') {
    const round = Math.min(3, Math.max(1, parseInt(arg || '1', 10)));
    const ids = roundIds(round);
    console.log(`--- ${jobKey}: generating 6 i2i variants (round ${round}: ${ids[0]}..${ids[5]}) from ${path.basename(job.refImg)} ---`);
    for (let i = 0; i < ids.length; i++) {
      const { key, prompt } = promptFor(job, round, i);
      await generateVariant(zai, job, ids[i], prompt, key);
      await sleep(1000);
    }
  } else if (stage === 'crop') {
    console.log('--- Face crops (Haar) ---');
    execFileSync('python3', ['/home/z/my-project/scripts/wardrobe-crop.py', job.cropJob], { stdio: 'inherit' });
  } else if (stage === 'fixcrops') {
    await stageFixCrops(zai, job);
  } else if (stage === 'score') {
    await stageScore(zai, job);
  } else if (stage === 'wardrobe') {
    await stageWardrobe(zai, job);
  } else if (stage === 'install') {
    const results = loadResults(job);
    await stageInstall(job, results, arg);
  } else if (stage === 'final') {
    await stageFinal(zai, job);
  } else {
    console.error(`unknown stage: ${stage}`);
    process.exit(1);
  }
}

main().catch(err => { console.error('FATAL:', err?.message || err); process.exit(1); });

# TTS and narration audio

Depth for the `tts` slot: provider setup, request shape, and how to prove
what is stored.

## Provider setup
Preset `minimax-tts` (registry id `minimax-tts`), default base URL
`https://api.minimaxi.com`, default model `speech-2.8-hd`, default voice
`female-yujie`. The key lives in the environment only:

```yaml
providers:
  minimax-tts:
    preset: minimax-tts
    apiKey: ${MINIMAX_TTS_API_KEY}
slots:
  tts: minimax-tts:speech-2.8-hd
```

The TTS endpoint is `{baseUrl}/v1/t2a_v2` (so
`https://api.minimaxi.com/v1/t2a_v2`); `https://api.minimax.chat` accepts the
same key. Request body the app sends:

```json
{"model":"speech-2.8-hd","text":"...","stream":false,"output_format":"hex",
 "voice_setting":{"voice_id":"female-yujie","speed":1.0,"vol":1,"pitch":0},
 "audio_setting":{"sample_rate":32000,"bitrate":128000,"format":"mp3","channel":1},
 "language_boost":"auto"}
```

Auth: `Authorization: Bearer <key>`. The response carries hex audio in
`data.audio`.

Common Chinese voices: `female-yujie`, `male-qn-jingying`, `female-shaonv`,
`Chinese (Mandarin)_Gentleman`, `Chinese (Mandarin)_News_Anchor`,
`Chinese (Mandarin)_Warm_Girl`, `Chinese (Mandarin)_Radio_Host`.

## Slot vs workspace
`openmaic.yml` writes the server default; a workspace assignment wins over it.
A workspace set to `browser-native-tts` (no key, synthesized in the browser)
silences server-side narration. Inspect and fix with `GET /api/model-config`
(`slots[].source` is `default` vs `workspace`) and `PUT /api/model-config`
(`{"revision":n,"change":{"kind":"slots","clear":["tts"]}}`).

## Where audio lives
- Server-side generation narrates each speech line and stores an asset:
  ids look like `ast_<hash>`, in `asset_entries` (+ bytes in `asset_blobs`),
  mime `audio/mpeg` or `audio/mp3`.
- The editor's per-scene "全部配音" (专业模式 → 底部「全部配音」) does the same
  from the browser; ids also land in `asset_entries`.
- The scene document carries the reference: `document_scenes.data` holds
  `audioId` on each speech action; `document_asset_refs` maps
  (stage_id, scene_id) → asset_id.

Verify with SQL (postgres `openmaic` db):

```sql
-- assets and their bytes
select a.id, a.mime, b.byte_size from asset_entries a
  join asset_blobs b on b.content_hash = a.content_hash
 where a.id in (select asset_id from document_asset_refs where stage_id = '<stage>');

-- which scenes of a course have audio
select s.scene_order, count(*) from document_asset_refs r
  join document_scenes s on s.id = r.scene_id
 where r.stage_id = '<stage>' group by 1 order by 1;

-- how many speech actions still lack an audioId (the document holds them as JSON)
select count(*) from document_scenes where stage_id = '<stage>'
  and data::text not like '%audioId%';
```

## Semantics to remember
- "全部配音" covers the **current scene only**; each scene needs its own click
  (the button iterates the current scene's speech actions and saves after
  every line).
- A course generated with `tts: null` has speech actions but zero audio
  assets; playback is silent until the lines are narrated.
- Browser-native TTS cannot manage timeline audio (preview / regenerate /
  全部配音) — the notice in the UI says so; switch the slot to a hosted
  provider first.

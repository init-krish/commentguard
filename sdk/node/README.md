# @commentguard/sdk

The official Node.js / TypeScript SDK for **CommentGuard** — an open-source, self-hostable toxic comment moderation API. A drop-in replacement for Google's Perspective API.

## Installation

```bash
npm install @commentguard/sdk
# or
yarn add @commentguard/sdk
# or
pnpm add @commentguard/sdk
```

## Quick Start

```typescript
import { CommentGuard } from '@commentguard/sdk';

// Initialize with your self-hosted CommentGuard URL
// Defaults to http://localhost:8000 if not provided
const guard = new CommentGuard({
  endpoint: 'http://localhost:8000'
});

async function run() {
  const result = await guard.moderate('You are terrible!');

  if (result.decision === 'block') {
    console.log('Comment blocked!');
    console.log(`Toxicity score: ${result.toxic_prob}`);
    console.log(`Categories: ${result.categories.join(', ')}`);
  }
}

run();
```

## API Reference

### `moderate(text: string, options?: ModerateOptions)`

Classify a single comment across 6 toxicity categories (toxic, severe_toxic, obscene, threat, insult, identity_hate).

```typescript
const result = await guard.moderate('Go away', {
  threshold: 0.8,    // Override default toxicity threshold
  site: 'youtube'    // Optional site context
});
```

### `moderateBatch(texts: string[], options?: ModerateOptions)`

Efficiently classify up to 100 comments in a single request.

```typescript
const batch = await guard.moderateBatch([
  'Hello world',
  'I hate you',
  'Have a nice day'
]);

console.log(`Found ${batch.toxic_count} toxic comments out of ${batch.total}`);
console.log(batch.results[1].categories); // ['toxic', 'insult']
```

### `submitFeedback(text: string, correctLabel: string, predictedLabel: string)`

Report false positives/negatives to improve your model over time.

```typescript
// If the model wrongly flagged a clean comment as toxic
await guard.submitFeedback(
  'I killed that workout today', 
  'non_toxic', 
  'toxic'
);
```

### `getStats()`

Get live analytics from your moderation server.

```typescript
const stats = await guard.getStats();
console.log(`Total processed: ${stats.total}`);
console.log(`Current toxicity rate: ${stats.toxic_rate}%`);
console.dir(stats.by_category);
```

## Types

The SDK is written in TypeScript and exports full typings for all requests and responses.

```typescript
import type { 
  ModerateResponse, 
  BatchResponse, 
  CategoryScores,
  CommentGuardConfig
} from '@commentguard/sdk';
```

## License

Apache-2.0

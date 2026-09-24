'use client';

// ponytail: standalone demo page, hardcoded to the old ML backend's MJPEG
// endpoint (127.0.0.1:8000) -- not wired through services/api.ts since that
// targets the new /api/v1 backend, which has no camera/model integration.
export default function LivePage() {
  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 16 }}>Live Detection Feed</h1>
      <img
        src="http://127.0.0.1:8000/video_feed"
        alt="Live fall-detection camera feed"
        style={{ maxWidth: '100%', border: '1px solid #333' }}
      />
    </div>
  );
}

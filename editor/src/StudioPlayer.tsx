import React from "react";
import { Player, type PlayerRef } from "@remotion/player";
import { Preview } from "./Preview";
import type { Project, View } from "./model";

// Keep transport/playhead updates outside the Player render tree.
export const StudioPlayer = React.memo(function StudioPlayer({
  playerRef,
  project,
  view,
}: {
  playerRef: React.RefObject<PlayerRef | null>;
  project: Project;
  view: View;
}) {
  const p = project.plan;
  return (
    <Player
      ref={playerRef}
      component={Preview}
      inputProps={{ project, view }}
      durationInFrames={p.duration_frames}
      compositionWidth={p.export.width}
      compositionHeight={p.export.height}
      fps={p.fps}
      controls={false}
      clickToPlay={false}
      style={{ width: "100%", height: "100%" }}
      errorFallback={({ error }: { error: Error }) => (
        <div className="preview-error">
          Không thể phát preview: {error.message}
        </div>
      )}
    />
  );
});

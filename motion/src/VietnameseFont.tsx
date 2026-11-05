import React, { useEffect, useState } from "react";
import {
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
} from "remotion";

export const VIETNAMESE_FONT = "Be Vietnam Pro";
const loads = new Map<string, Promise<void>>();

export const VietnameseFont: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [handle] = useState(() =>
    delayRender("Loading bundled Vietnamese font"),
  );
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let mounted = true;
    const regular = staticFile("fonts/BeVietnamPro-Regular.ttf");
    const bold = staticFile("fonts/BeVietnamPro-Bold.ttf");
    const key = regular + "|" + bold;
    let load = loads.get(key);
    if (!load) {
      load = Promise.all(
        [
          [regular, "400"],
          [bold, "700"],
        ].map(async ([url, weight]) => {
          const face = new FontFace(VIETNAMESE_FONT, `url("${url}")`, {
            weight,
            style: "normal",
          });
          await face.load();
          document.fonts.add(face);
        }),
      ).then(() => undefined);
      loads.set(key, load);
    }
    load
      .then(() => {
        if (mounted) setReady(true);
        continueRender(handle);
      })
      .catch((error) => {
        loads.delete(key);
        cancelRender(
          new Error("Cannot load bundled Vietnamese font: " + String(error)),
        );
      });
    return () => {
      mounted = false;
      continueRender(handle);
    };
  }, [handle]);
  return ready ? <>{children}</> : null;
};

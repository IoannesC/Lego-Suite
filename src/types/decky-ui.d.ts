import type { CSSProperties } from "react";

declare module "@decky/ui" {
  interface ButtonItemProps {
    style?: CSSProperties;
  }
  interface PanelSectionRowProps {
    bottomSeparator?: string;
  }
}

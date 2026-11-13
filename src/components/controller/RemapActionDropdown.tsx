import { FC } from "react";
import { DropdownItem } from "@decky/ui";
import { RemapActions, RemappableButtons } from "../../backend/constants";
import { useRemapAction } from "../../hooks/controller";
import t from "../../i18n/i18n";

type PropType = {
  btn: RemappableButtons;
};

const ACTION_I18N_KEYS: Record<string, string> = {
  DISABLED: "REMAP_ACTION_DISABLED",
  A: "REMAP_ACTION_A",
  B: "REMAP_ACTION_B",
  X: "REMAP_ACTION_X",
  Y: "REMAP_ACTION_Y",
  LEFT_BUMPER: "REMAP_ACTION_LB",
  LEFT_TRIGGER: "REMAP_ACTION_LT",
  RIGHT_BUMPER: "REMAP_ACTION_RB",
  RIGHT_TRIGGER: "REMAP_ACTION_RT",
  LEFT_STICK_CLICK: "REMAP_ACTION_L3",
  RIGHT_STICK_CLICK: "REMAP_ACTION_R3",
  DPAD_UP: "REMAP_ACTION_DPAD_UP",
  DPAD_DOWN: "REMAP_ACTION_DPAD_DOWN",
  DPAD_LEFT: "REMAP_ACTION_DPAD_LEFT",
  DPAD_RIGHT: "REMAP_ACTION_DPAD_RIGHT",
  VIEW: "REMAP_ACTION_VIEW",
  MENU: "REMAP_ACTION_MENU",
};

const RemapActionDropdown: FC<PropType> = ({ btn }) => {
  const { remapAction, setRemapAction } = useRemapAction(btn);
  const dropdownOptions = Object.values(RemapActions).map((action) => {
    const key = ACTION_I18N_KEYS[action];
    const fallback = action.split("_").join(" ");
    const label = key ? t(key, fallback) : fallback;
    return {
      data: action,
      label,
      value: action,
    };
  });

  return (
    <div>
      <DropdownItem
        bottomSeparator="none"
        rgOptions={dropdownOptions.map((o) => {
          return {
            data: o.data,
            label: o.label,
            value: o.value,
          };
        })}
        selectedOption={
          dropdownOptions.find((o) => {
            return o.data === remapAction;
          })?.data || RemapActions.DISABLED
        }
        onChange={(value: any) => {
          setRemapAction(value.data);
        }}
      />
    </div>
  );
};

export default RemapActionDropdown;

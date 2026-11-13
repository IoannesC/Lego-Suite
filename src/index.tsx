import { definePlugin } from "@decky/api";
import { getSettings, setValuesForGameId } from "./backend/utils";
import { store } from "./redux-modules/store";
import {
  acPowerEventListener,
  currentGameInfoListener,
  resumeFromSuspendEventListener,
  suspendEventListener,
} from "./steamListeners";
import { currentGameIdListener } from "./backend/currentGameIdListener";
import { clearAlsListener } from "./backend/alsListener";
import { updateInitialLoad } from "./redux-modules/settingsSlice";
import { cleanupAction, setInitialState } from "./redux-modules/extraActions";
import { fetchPowerControlInfo } from "./redux-modules/thunks";
import AppContainer from "./App";
import { initializePollingStore } from "./redux-modules/pollingMiddleware";
import logo from "../assets/Icon.png";

export default definePlugin(() => {
  initializePollingStore(store);

  
  getSettings().then((result) => {
    const results = (result || {}) as Record<string, any>;

    store.dispatch(
      updateInitialLoad({
        ...results,
      }),
    );
    store.dispatch(setInitialState(results));
    store.dispatch(fetchPowerControlInfo());

    setTimeout(() => {
      setValuesForGameId({ gameId: "default" });
    }, 0);
  });

  const unregisterCurrentGameListener = currentGameInfoListener();
  const unregisterRemapperGameIdListener = currentGameIdListener();
  const unregisterResumeListener = resumeFromSuspendEventListener();
  const unregisterSuspendListener = suspendEventListener();

  let unregisterAcPowerListener: (() => void) | undefined;

  acPowerEventListener().then((unregister) => {
    unregisterAcPowerListener = unregister;
  });

  return {
    name: "LeGO Suite",
    content: <AppContainer />,
    icon: (
      <img
        src={logo}
        style={{
          width: "1rem",
          filter:
            "invert(100%) sepia(0%) saturate(2%) hue-rotate(157deg) brightness(107%) contrast(101%)",
        }}
      />
    ),
    onDismount: () => {
      try {
        store.dispatch(cleanupAction());
        clearAlsListener();
        if (unregisterCurrentGameListener) unregisterCurrentGameListener();
        if (unregisterRemapperGameIdListener)
          unregisterRemapperGameIdListener();
        if (
          unregisterAcPowerListener &&
          typeof unregisterAcPowerListener === "function"
        )
          unregisterAcPowerListener();
        if (
          unregisterSuspendListener &&
          typeof unregisterSuspendListener === "function"
        )
          unregisterSuspendListener();
        if (
          unregisterResumeListener &&
          typeof unregisterResumeListener === "function"
        )
          unregisterResumeListener();
      } catch (e) {
        console.error(e);
      }
    },
  };
});

// El tiempo se va como agua entre los dedos. Aprovecha el tuyo

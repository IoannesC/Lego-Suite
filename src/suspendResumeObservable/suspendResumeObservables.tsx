import { getMobxObservable } from "./getMobxObservable";



const mobxAdministrationSymbol = Symbol("mobx administration");
const mobxStoredAnnotationsSymbol = Symbol("mobx-stored-annotations");

interface SuspendResumeStoreType {
  m_bResuming: boolean;
  m_bShowResumeUI: boolean;
  m_bSuspending: boolean;
  m_cSuspendBlockers: number;
  m_eSuspendResumeProgress: number;
  m_nSuspendSleepMS: number;

  
  
  
  
  
  
  

  [mobxAdministrationSymbol]: unknown;
  [mobxStoredAnnotationsSymbol]: unknown;
}

declare global {
  
  let SuspendResumeStore: SuspendResumeStoreType;
}

export function getSuspendResumeObservable() {
  const suspendingMobXObservable = getMobxObservable(
    SuspendResumeStore,
    "m_bSuspending",
  );
  return suspendingMobXObservable;
}












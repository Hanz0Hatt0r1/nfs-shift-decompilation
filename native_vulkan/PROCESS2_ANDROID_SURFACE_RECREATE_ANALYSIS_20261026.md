# Android surface-recreation boundary — 2026-10-26

The PM4-ordering Android candidate displayed the original loading screen and
legal disclaimer. The retained runtime log contains 515 successful indexed-draw
batches (2,960 draw packets), 515 accepted Copy/Convert operations, and no
presenter refresh failures. Its frame-500 Vulkan readback contains 17,951
non-black pixels and matches the retail disclaimer output.

The last 14-draw batch was submitted at 13:04:19.932 MSK. Four subsequent
`menu_background.xml` open attempts failed at 13:04:20.290–13:04:20.295. The
log contains no later guest batch before the lifecycle disturbance. Process 1's
provided trace places `surfaceDestroyed`/`nativePause` at 13:06:37, followed by
a Vulkan outdated-present result at 13:06:37.478 and abandoned BufferQueue
messages during later resume. The file misses are close in time to the final
batch but do not establish why the guest stopped producing commands.

Read-only inspection of ReXGlue SDK commit
`d6ed02eea517a34166e3a1d0ef8e5ab9c5ca8253` found a plausible separate Android
surface-rebind defect. SDL replaces
`SDL_PROP_WINDOW_ANDROID_WINDOW_POINTER` when `surfaceCreated` fires, but the
ReX `AndroidNativeWindowSurface` wrapper retains the raw pointer captured when
the presenter was attached. Android's current resize notification does not
reliably signal replacement when dimensions are unchanged. Vulkan presenter
recovery retries using that existing wrapper. This can account for the failed
presentation after resume; it cannot account for the guest's earlier idle
period. The cause is plausible and source-backed, but not proven as the sole
cause of the abandoned queue.

Process 2 did not edit the shared SDK or Process 1 files. The diagnosis and
smallest rebind direction were sent to Process 1 for integration ownership. A
regression should replace the Android native window at the same dimensions and
verify disconnect-before-release, rebind to the new pointer, and recovery from
`VK_ERROR_OUT_OF_DATE_KHR` / `VK_ERROR_SURFACE_LOST_KHR`.

Evidence: [run record](../evidence/process2_redmi_surface_recreate_ring_idle_20261026.json),
[compressed guest log](../evidence/process2_redmi_pm4_live_latest_20261026.log.gz).
This remains a startup/disclaimer capture, not proof of menu, race, sustained
cutscene, or full retail parity. Android Vulkan validation layers were not
available in the device run.

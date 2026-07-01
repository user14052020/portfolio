"use client";

/* eslint-disable @next/next/no-img-element -- Gallery images are CMS-managed URLs and may not be known at build time. */

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { IconChevronLeft, IconChevronRight, IconMaximize, IconMinimize, IconX } from "@tabler/icons-react";

import { cn } from "@/shared/lib/cn";

export type ProjectScreenshot = {
  id: number;
  url: string;
  alt: string;
};

type ProjectScreenshotGalleryProps = {
  screenshots: ProjectScreenshot[];
  title: string;
  className?: string;
};

export function ProjectScreenshotGallery({
  screenshots,
  title,
  className,
}: ProjectScreenshotGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const normalizedScreenshots = useMemo(() => screenshots.filter((item) => item.url), [screenshots]);

  useEffect(() => {
    setActiveIndex(0);
  }, [normalizedScreenshots.length]);

  if (normalizedScreenshots.length === 0) {
    return null;
  }

  function openViewer(index: number) {
    setActiveIndex(index);
    setIsViewerOpen(true);
  }

  return (
    <div
      className={cn(
        "relative isolate overflow-hidden rounded-lg border border-black/10 bg-[#0d0f14] shadow-[0_24px_70px_rgba(15,23,42,0.16)]",
        className,
      )}
    >
      <div className="relative aspect-[16/9] min-h-[250px] w-full overflow-hidden p-2 sm:p-3">
        {normalizedScreenshots.length === 1 ? (
          <SingleScreenshotPreview
            screenshot={normalizedScreenshots[0]}
            title={title}
            onOpen={() => openViewer(0)}
          />
        ) : (
          <>
            <MobileFirstScreenshot
              screenshot={normalizedScreenshots[0]}
              count={normalizedScreenshots.length}
              title={title}
              onOpen={() => openViewer(0)}
            />
            <DesktopScreenshotGrid screenshots={normalizedScreenshots} title={title} onOpen={openViewer} />
          </>
        )}
      </div>

      {isViewerOpen ? (
        <ScreenshotViewer
          screenshots={normalizedScreenshots}
          activeIndex={activeIndex}
          onActiveIndexChange={setActiveIndex}
          onClose={() => setIsViewerOpen(false)}
        />
      ) : null}
    </div>
  );
}

export function openEncodedDemoUrl(demoUrlToken: string) {
  const demoUrl = decodeDemoUrlToken(demoUrlToken);

  if (!demoUrl || typeof document === "undefined") {
    return;
  }

  const anchor = document.createElement("a");
  anchor.href = demoUrl;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  anchor.referrerPolicy = "no-referrer";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

function decodeDemoUrlToken(demoUrlToken: string) {
  try {
    const bytes = Uint8Array.from(window.atob(demoUrlToken), (char) => char.charCodeAt(0));
    const decodedUrl = new TextDecoder().decode(bytes);
    const parsedUrl = new URL(decodedUrl);

    return parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:" ? parsedUrl.toString() : null;
  } catch {
    return null;
  }
}

function SingleScreenshotPreview({
  screenshot,
  title,
  onOpen,
}: {
  screenshot: ProjectScreenshot;
  title: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={`Open ${title} screenshot`}
      onClick={onOpen}
      className="absolute inset-2 flex items-center justify-center overflow-hidden rounded-md bg-black text-left sm:inset-3"
    >
      <img
        src={screenshot.url}
        alt={screenshot.alt}
        loading="lazy"
        decoding="async"
        className="h-full w-full object-contain object-center"
      />
    </button>
  );
}

function MobileFirstScreenshot({
  screenshot,
  count,
  title,
  onOpen,
}: {
  screenshot: ProjectScreenshot;
  count: number;
  title: string;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={`Open ${title} screenshots`}
      onClick={onOpen}
      className="group absolute inset-2 flex items-center justify-center overflow-hidden rounded-md bg-black text-left sm:hidden"
    >
      <img
        src={screenshot.url}
        alt={screenshot.alt}
        loading="lazy"
        decoding="async"
        className="max-h-full max-w-full object-contain object-center"
      />
      <GalleryOverlay count={count} />
    </button>
  );
}

function DesktopScreenshotGrid({
  screenshots,
  title,
  onOpen,
}: {
  screenshots: ProjectScreenshot[];
  title: string;
  onOpen: (index: number) => void;
}) {
  const visibleScreenshots = screenshots.slice(0, 6);
  const hiddenCount = Math.max(screenshots.length - visibleScreenshots.length, 0);

  return (
    <div className={cn("hidden h-full gap-2 sm:grid", resolveGridClassName(screenshots.length))}>
      {visibleScreenshots.map((screenshot, index) => {
        const isLastVisible = index === visibleScreenshots.length - 1 && hiddenCount > 0;

        return (
          <button
            key={`${screenshot.id}-${screenshot.url}`}
            type="button"
            aria-label={`Open ${title} screenshot ${index + 1}`}
            onClick={() => onOpen(index)}
            className={cn(
              "group relative h-full w-full min-h-0 overflow-hidden rounded-md bg-black text-left",
              screenshots.length === 1 && "grid place-items-center",
              resolveTileClassName(screenshots.length, index),
            )}
          >
            <img
              src={screenshot.url}
              alt={screenshot.alt}
              loading="lazy"
              decoding="async"
              className={cn(
                "transition duration-300",
                screenshots.length === 1
                  ? "block h-full w-full object-contain object-center"
                  : "h-full w-full object-cover group-hover:scale-[1.035]",
              )}
            />
            <span className="absolute inset-0 bg-black/0 transition group-hover:bg-black/16" />
            {isLastVisible ? (
              <span className="absolute inset-0 grid place-items-center bg-black/54 text-lg font-semibold text-white">
                +{hiddenCount}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function GalleryOverlay({ count }: { count: number }) {
  return (
    <>
      <span className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/72 to-transparent" />
      <span className="absolute bottom-3 right-3 inline-flex items-center gap-2 rounded-md bg-black/80 px-3 py-2 text-xs font-semibold text-white shadow-[0_12px_32px_rgba(0,0,0,0.34)] ring-1 ring-white/10">
        <IconMaximize className="h-4 w-4" aria-hidden />
        {count}
      </span>
    </>
  );
}

function ScreenshotViewer({
  screenshots,
  activeIndex,
  onActiveIndexChange,
  onClose,
}: {
  screenshots: ProjectScreenshot[];
  activeIndex: number;
  onActiveIndexChange: (index: number) => void;
  onClose: () => void;
}) {
  const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const activeScreenshot = screenshots[activeIndex] ?? screenshots[0];
  const canNavigate = screenshots.length > 1;

  useEffect(() => {
    setPortalTarget(document.body);
  }, []);

  useEffect(() => {
    if (!portalTarget) {
      return;
    }

    const dialogElement = dialogRef.current;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = "";
      if (dialogElement && isElementFullscreen(dialogElement)) {
        void exitBrowserFullscreen();
      }
    };
  }, [portalTarget]);

  useEffect(() => {
    function syncFullscreenState() {
      setIsFullscreen(Boolean(dialogRef.current && isElementFullscreen(dialogRef.current)));
    }

    document.addEventListener("fullscreenchange", syncFullscreenState);
    document.addEventListener("webkitfullscreenchange", syncFullscreenState);
    document.addEventListener("msfullscreenchange", syncFullscreenState);

    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      document.removeEventListener("webkitfullscreenchange", syncFullscreenState);
      document.removeEventListener("msfullscreenchange", syncFullscreenState);
    };
  }, []);

  function showPrevious() {
    onActiveIndexChange((activeIndex - 1 + screenshots.length) % screenshots.length);
  }

  function showNext() {
    onActiveIndexChange((activeIndex + 1) % screenshots.length);
  }

  async function toggleFullscreen() {
    const dialogElement = dialogRef.current;
    if (!dialogElement) {
      return;
    }

    if (isFullscreen) {
      if (isElementFullscreen(dialogElement)) {
        await exitBrowserFullscreen();
      }
      setIsFullscreen(false);
      return;
    }

    const didEnterBrowserFullscreen = await enterBrowserFullscreen(dialogElement);
    setIsFullscreen(didEnterBrowserFullscreen || true);
  }

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
      if (event.key === "ArrowLeft" && canNavigate) {
        showPrevious();
      }
      if (event.key === "ArrowRight" && canNavigate) {
        showNext();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const dialog = (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      className={cn(
        "fixed inset-0 z-[2147483647] grid h-dvh bg-black/90 text-white outline-none backdrop-blur-[2px]",
        isFullscreen ? "p-2 sm:p-4" : "p-3 sm:p-6",
      )}
    >
      <div className={cn("grid h-full min-h-0 gap-3", isFullscreen ? "grid-rows-[auto_minmax(0,1fr)]" : "grid-rows-[auto_minmax(0,1fr)_auto]")}>
        <div className="flex items-center justify-between gap-4">
          <p className="rounded-md bg-black/72 px-3 py-2 text-sm font-semibold text-white shadow-[0_14px_34px_rgba(0,0,0,0.35)] ring-1 ring-white/10">
            {activeIndex + 1} / {screenshots.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              aria-label={isFullscreen ? "Exit fullscreen" : "Open fullscreen"}
              onClick={() => void toggleFullscreen()}
              className={cn(viewerControlClassName, "hidden lg:grid")}
            >
              {isFullscreen ? <IconMinimize className="h-5 w-5" aria-hidden /> : <IconMaximize className="h-5 w-5" aria-hidden />}
            </button>
            <button type="button" aria-label="Close screenshot viewer" onClick={onClose} className={viewerControlClassName}>
              <IconX className="h-5 w-5" aria-hidden />
            </button>
          </div>
        </div>

        <div className="relative min-h-0 overflow-y-auto overscroll-contain rounded-sm sm:overflow-hidden">
          <div className="grid min-h-full justify-items-center" style={{ alignItems: "safe center" }}>
            <img
              src={activeScreenshot.url}
              alt={activeScreenshot.alt}
              decoding="async"
              className="block h-auto max-h-full w-auto max-w-full object-contain object-center"
            />
          </div>

          {canNavigate ? (
            <>
              <ViewerArrow direction="previous" onClick={showPrevious} />
              <ViewerArrow direction="next" onClick={showNext} />
            </>
          ) : null}
        </div>

        {canNavigate && !isFullscreen ? (
          <div className="mx-auto hidden max-w-full gap-2 overflow-x-auto pb-1 lg:flex">
            {screenshots.map((screenshot, index) => (
              <button
                key={`${screenshot.id}-${screenshot.url}-thumb`}
                type="button"
                aria-label={`Show screenshot ${index + 1}`}
                onClick={() => onActiveIndexChange(index)}
                className={cn(
                  "h-14 w-20 shrink-0 overflow-hidden rounded-sm border transition sm:h-16 sm:w-24",
                  index === activeIndex
                    ? "border-white shadow-[0_10px_26px_rgba(0,0,0,0.32)]"
                    : "border-black/60 opacity-64 hover:opacity-100",
                )}
              >
                <img
                  src={screenshot.url}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  className="h-full w-full object-cover"
                />
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );

  return portalTarget ? createPortal(dialog, portalTarget) : null;
}

const viewerControlClassName =
  "grid h-10 w-10 place-items-center rounded-md border border-black/70 bg-black/80 text-white shadow-[0_14px_34px_rgba(0,0,0,0.38)] ring-1 ring-white/10 transition hover:bg-black";

type FullscreenDocument = Document & {
  webkitFullscreenElement?: Element | null;
  msFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void> | void;
  msExitFullscreen?: () => Promise<void> | void;
};

type FullscreenElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
  msRequestFullscreen?: () => Promise<void> | void;
};

function getFullscreenElement() {
  const fullscreenDocument = document as FullscreenDocument;

  return (
    document.fullscreenElement ??
    fullscreenDocument.webkitFullscreenElement ??
    fullscreenDocument.msFullscreenElement ??
    null
  );
}

function isElementFullscreen(element: HTMLElement) {
  return getFullscreenElement() === element;
}

async function enterBrowserFullscreen(element: HTMLElement) {
  const fullscreenElement = element as FullscreenElement;
  const requestFullscreen =
    fullscreenElement.requestFullscreen?.bind(fullscreenElement) ??
    fullscreenElement.webkitRequestFullscreen?.bind(fullscreenElement) ??
    fullscreenElement.msRequestFullscreen?.bind(fullscreenElement);

  if (!requestFullscreen) {
    return false;
  }

  try {
    await requestFullscreen();
    return true;
  } catch {
    return false;
  }
}

async function exitBrowserFullscreen() {
  const fullscreenDocument = document as FullscreenDocument;
  const exitFullscreen =
    document.exitFullscreen?.bind(document) ??
    fullscreenDocument.webkitExitFullscreen?.bind(fullscreenDocument) ??
    fullscreenDocument.msExitFullscreen?.bind(fullscreenDocument);

  if (!exitFullscreen) {
    return;
  }

  try {
    await exitFullscreen();
  } catch {
    // The CSS fullscreen fallback can be active even when browser fullscreen is unavailable.
  }
}

function ViewerArrow({ direction, onClick }: { direction: "previous" | "next"; onClick: () => void }) {
  const Icon = direction === "previous" ? IconChevronLeft : IconChevronRight;

  return (
    <button
      type="button"
      aria-label={direction === "previous" ? "Previous screenshot" : "Next screenshot"}
      onClick={onClick}
      className={cn(
        "absolute top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-black/70 bg-black/80 text-white shadow-[0_16px_40px_rgba(0,0,0,0.42)] ring-1 ring-white/10 backdrop-blur transition hover:bg-black sm:h-12 sm:w-12",
        direction === "previous" ? "left-1 sm:left-4" : "right-1 sm:right-4",
      )}
    >
      <Icon className="h-6 w-6" aria-hidden />
    </button>
  );
}

function resolveGridClassName(count: number) {
  if (count === 1) {
    return "grid-cols-1 grid-rows-1";
  }
  if (count === 2) {
    return "grid-cols-2 grid-rows-1";
  }
  if (count === 3) {
    return "grid-cols-3 grid-rows-2";
  }
  if (count === 4) {
    return "grid-cols-2 grid-rows-2";
  }
  return "grid-cols-3 grid-rows-2";
}

function resolveTileClassName(count: number, index: number) {
  if (count === 1) {
    return "";
  }
  if (count === 3 && index === 0) {
    return "row-span-2";
  }
  return "";
}

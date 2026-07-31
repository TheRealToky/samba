import { Component, ErrorInfo, ReactNode } from "react";

// The authenticated routes are React.lazy imports of hashed chunks. When the
// file a chunk name points at is not there — the tab is holding an index.html
// from an older build, or a load-balanced replica is serving a different one —
// the dynamic import rejects. Without a boundary that rejection propagates to
// the root, React unmounts the entire tree, and the user gets a blank page with
// nothing in the UI to act on. Catch it here instead.
const CHUNK_ERROR =
  /(loading (css )?chunk|dynamically imported module|importing a module script failed|unexpected token '<')/i;

// One automatic reload per tab, ever. A stale index.html is fixed by fetching
// the current one, but if the reload lands on a replica that is still wrong we
// must not spin — after that the user gets the message and decides.
const RELOAD_FLAG = "samba_chunk_reload";

function isChunkError(error: Error): boolean {
  return CHUNK_ERROR.test(error.message);
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error", error, info.componentStack);
    if (isChunkError(error) && !sessionStorage.getItem(RELOAD_FLAG)) {
      sessionStorage.setItem(RELOAD_FLAG, "1");
      window.location.reload();
    }
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const stale = isChunkError(error);
    return (
      <div className="centered">
        <div className="panel" style={{ maxWidth: 460, textAlign: "center" }}>
          <h2>{stale ? "This page is out of date" : "Something went wrong"}</h2>
          <p className="panel-note">
            {stale
              ? "SAMBA was updated while this tab was open, so part of the dashboard could not be loaded. Reloading picks up the current version."
              : error.message || "An unexpected error stopped the page from loading."}
          </p>
          <button
            className="btn-ghost"
            style={{ marginTop: 14 }}
            onClick={() => {
              sessionStorage.removeItem(RELOAD_FLAG);
              window.location.reload();
            }}
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}

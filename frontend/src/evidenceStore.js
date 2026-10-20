// Audio files attached on the Evidence page, kept in memory so the Variants page can analyse them.
// (sessionStorage can only hold their names; after a page reload the files must be attached again.)
let files = [];

export function setEvidenceFiles(next) {
  files = Array.from(next || []);
}

export function getEvidenceFiles() {
  return files;
}

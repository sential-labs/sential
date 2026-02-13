import fg from "fast-glob";
import path from "node:path";
import { SentialError } from "../errors";

const SUPPORTED_OSES = ["win32", "darwin", "linux"] as const;
type SupportedOs = (typeof SUPPORTED_OSES)[number];
const SUPPORTED_ARCHS = ["arm64", "x64"] as const;
type SupportedArch = (typeof SUPPORTED_ARCHS)[number];

function IsSupportedOs(os: string): os is SupportedOs {
  return SUPPORTED_OSES.includes(os as SupportedOs);
}

function isSupportedArch(arch: string): arch is SupportedArch {
  return SUPPORTED_ARCHS.includes(arch as SupportedArch);
}

function getSystem(): SupportedOs {
  const system = process.platform;

  if (!IsSupportedOs(system)) {
    throw new SentialError("Your Operating System is not supported.");
  }

  return system;
}

function getArchitecture(): SupportedArch {
  const arch = process.arch;

  if (!isSupportedArch(arch)) {
    throw new SentialError("Your System Architecture is not supported.");
  }

  return arch;
}

function buildBinaryPattern(system: SupportedOs, arch: SupportedArch): string {
  if (system == "win32") {
    return `ctags-windows-${arch}-*.exe`;
  }

  return `ctags-${system}-${arch}-*`;
}

export async function getCtagsPath(): Promise<string> {
  const cwd = process.cwd();
  const binDir = path.join(cwd, "bin");

  const system = getSystem();
  const arch = getArchitecture();
  const pattern = buildBinaryPattern(system, arch);

  const matches = await fg.async(path.join(binDir, pattern));

  const [firstMatch] = matches;
  if (!firstMatch) {
    throw new Error(
      `No ctags binary found matching pattern ${pattern} in ${binDir}`,
    );
  }

  return firstMatch;
}

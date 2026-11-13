// Example from a Frappe app's Drive module: its imports and API paths are that app's.
// Copy the shape, not the code.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRequestContext } from "@playwright/test";
import { createDocument, createFolder, uploadFile, type DriveNode } from "../drive-backed-apps/helpers/drive";

const fixture = (name: string) => readFileSync(resolve(__dirname, "fixtures", name));

export interface FolderContent {
	folders: DriveNode[];
	emptyFolder: DriveNode;
	document: DriveNode;
	sheet: DriveNode;
	notes: DriveNode;
	brief: DriveNode;
	logo: DriveNode;
}

/** Fills `parent` with the mix a real folder has: folders, native documents and uploaded files. */
export async function fillFolder(api: APIRequestContext, parent: string): Promise<FolderContent> {
	const emptyFolder = await createFolder(api, "Archive", parent);
	const folders = [
		await createFolder(api, "Design reviews", parent),
		await createFolder(api, "Quarterly planning", parent),
		emptyFolder,
	];
	const document = await createDocument(api, "Launch brief", "Writer Document", parent);
	const sheet = await createDocument(api, "Budget 2026", "Sheet", parent);
	const notes = await uploadFile(api, "Meeting notes.md", Buffer.from("# Notes\n\n- Ship it\n"), parent, "text/markdown");
	const brief = await uploadFile(api, "Quarter review.pdf", fixture("Quarter review.pdf"), parent, "application/pdf");
	const logo = await uploadFile(api, "Logo.png", fixture("Logo.png"), parent, "image/png");
	return { folders, emptyFolder, document, sheet, notes, brief, logo };
}

export function folderPath(node: Pick<DriveNode, "name">): string {
	return `/drive/f/${node.name}`;
}

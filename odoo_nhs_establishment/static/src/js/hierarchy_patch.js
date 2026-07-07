import { patch } from "@web/core/utils/patch";
import { HierarchyNode, HierarchyModel } from "@web_hierarchy/hierarchy_model";
import { orderByToString } from "@web/search/utils/order_by";
import { _t } from "@web/core/l10n/translation";

// Helper to determine if a value is a fully loaded object (not a stub with only an id)
function isFullyLoadedObject(value) {
    return value instanceof Object && Object.keys(value).length > 1;
}

// Helper to get the correct Many2one ID
function getMany2oneFieldId(value) {
    if (!value) {
        return false;
    }
    if (typeof value === "number") {
        return value;
    }
    if (Array.isArray(value)) {
        return value[0];
    }
    return value.id || false;
}

// Patch HierarchyNode
patch(HierarchyNode.prototype, {
    get parentResId() {
        return this.parentNode?.resId || getMany2oneFieldId(this.data[this.parentFieldName]);
    },

    populateChildNodes() {
        this._nodes = [];
        const children = this.data[this.childFieldName] || [];
        if (
            children.length &&
            isFullyLoadedObject(children[0]) &&
            this.tree.forest.resIds.filter((resId) => resId === this.resId).length === 1
        ) {
            this.createChildNodes(children);
        }
    }
});

// Patch HierarchyModel
patch(HierarchyModel.prototype, {
    async fetchSubordinates(node) {
        const childFieldName = this.childFieldName || this.defaultChildFieldName;
        const children = node.data[childFieldName];
        if (children.length) {
            const nodesToUpdate = [];
            if (!isFullyLoadedObject(children[0])) {
                const childrenResIds = children.map((c) => (c && c.id) || c);
                const allNodeResIds = this.root.resIds;
                let existingChildResIds = childrenResIds.filter((childResId) => allNodeResIds.includes(childResId));
                if (existingChildResIds.length) {
                    // special case with result found with the search view
                    for (const tree of this.root.trees) {
                        if (
                            existingChildResIds.includes(tree.root.resId) &&
                            tree.root.id !== node.id
                        ) {
                            // don't re-root if both nodes are in the same tree
                            if (node.tree.id === tree.id) {
                                existingChildResIds = existingChildResIds.filter(
                                    (resId) => resId !== tree.root.resId
                                );
                                continue;
                            }
                            nodesToUpdate.push(tree.root);
                        }
                    }
                }
                const subordinates = await this.keepLast.add(
                    this._fetchSubordinates(node, existingChildResIds)
                );
                if (subordinates.length) {
                    node.data[childFieldName] = subordinates;
                }
            }
            const nodeToCollapse = this._searchNodeToCollapse(node);
            if (nodeToCollapse && !nodesToUpdate.includes(nodeToCollapse)) {
                nodeToCollapse.collapseChildNodes(true);
            }
            node.populateChildNodes();
            for (const n of nodesToUpdate) {
                n.setParentNode(node);
            }
            this.notify();
        }
    },

    async _fetchSubordinates(node, excludeResIds = null) {
        const childFieldName = this.childFieldName || this.defaultChildFieldName;
        let childrenResIds = (node.data[childFieldName] || []).map((c) => (c && c.id) || c);
        if (excludeResIds) {
            childrenResIds = childrenResIds.filter(
                (childResId) => !excludeResIds.includes(childResId)
            );
        }
        if (!childrenResIds.length) {
            return [];
        }
        const { records } = await this.orm.webSearchRead(
            this.resModel,
            [["id", "in", childrenResIds]],
            {
                specification: this._getFieldsSpec(),
                context: this.context,
                order: orderByToString(this.config.orderBy),
            }
        );
        if (!this.childFieldName) {
            await this._fetchDescendants(records);
        }
        return records;
    },

    _formatData(data) {
        const dataStringified = JSON.stringify(data);
        const recordsPerParentId = {};
        const recordPerId = {};
        for (const record of data) {
            recordPerId[record.id] = record;
            const parentId = getMany2oneFieldId(record[this.parentFieldName]);
            const parentIdStr = parentId ? parentId.toString() : "false";
            if (!(parentIdStr in recordsPerParentId)) {
                recordsPerParentId[parentIdStr] = [];
            }
            recordsPerParentId[parentIdStr].push(record);
        }
        const formattedData = [];
        const recordIds = []; // to check if we have only one arborescence to display otherwise we display the data as the kanban view
        for (let [parentIdStr, records] of Object.entries(recordsPerParentId)) {
            records = [...new Map(records.map((record) => [record.id, record])).values()];
            if (parentIdStr === "false" || !(parentIdStr in recordPerId)) {
                formattedData.push(...records);
            } else {
                const parentRecord = recordPerId[parentIdStr];
                if (recordIds.includes(parentRecord.id)) {
                    return JSON.parse(dataStringified);
                }
                const ancestorId = getMany2oneFieldId(parentRecord[this.parentFieldName]);
                const ancestorIdStr = ancestorId ? ancestorId.toString() : "false";
                if (ancestorIdStr in recordsPerParentId) {
                    recordIds.push(...recordsPerParentId[ancestorIdStr].map((r) => r.id));
                }
                parentRecord[this.childFieldName || this.defaultChildFieldName] = records;
            }
        }
        if (!formattedData.length && data?.length) {
            formattedData.push(recordPerId[Object.keys(recordsPerParentId)[0]]);
        }
        return formattedData;
    },

    async updateParentNode(nodeId, { parentNodeId, parentResId }) {
        const node = this.root.nodePerNodeId[nodeId];
        const resId = node.resId;
        // Validation.
        if (!node) {
            return;
        }
        const parentNode = parentNodeId ? this.root.nodePerNodeId[parentNodeId] : null;
        parentResId = parentResId || parentNode?.resId || false;
        const oldParentNode = node.parentNode;
        if (
            (parentNode && !this.validateUpdateParentNode(node, parentNode)) ||
            parentNode?.resId === oldParentNode?.resId
        ) {
            return;
        }
        // Hide the node while waiting for the server response.
        node.hidden = true;
        this.notify({ scrollTarget: "none" });
        // Update the parent server side.
        await this.mutex.exec(async () => {
            try {
                await this.updateParentId(node, parentResId);
            } catch (error) {
                // Show the node again since the operation failed, don't update the view.
                node.hidden = false;
                this.notify({ scrollTarget: "none" });
                throw error;
            }
        });
        // Reload impacted records.
        const domain = this.computeUpdateParentNodeDomain(node, parentResId, parentNode);
        const data = await this.orm.webSearchRead(this.resModel, domain, {
            specification: this._getFieldsSpec(),
            context: this.context,
            order: orderByToString(this.config.orderBy),
        });
        if (!data.length) {
            return this.reload();
        }
        const formattedData = this._formatData(data.records);
        // Validate that data coming from the server is still compatible with the current
        // configuration of the hierarchy.
        for (const record of formattedData) {
            if (getMany2oneFieldId(record[this.parentFieldName]) !== parentResId) {
                node.hidden = false;
                this.notify({ scrollTarget: "none" });
                this.notification.add(
                    _t(
                        `The parent of "%s" was successfully updated. Reloading records to account for other changes.`,
                        node.data.display_name || node.data.name
                    ),
                    { type: "success" }
                );
                return this.reload();
            }
        }
        // Handle the expanded tree.
        let nodeToCollapse;
        const treeExpanded = this._findTreeExpanded();
        const expandedParentNodeIds =
            treeExpanded?.root.descendantsParentNodes.map((node) => node.id) || [];
        if (!node.isLeaf || !expandedParentNodeIds.includes(parentNode?.id)) {
            // Handle cases where the expanded tree will be altered.
            // If node is not a leaf, the new expanded tree will contain its descendants.
            // If parentNode is not a parent in the current expanded tree, it will become one
            // in the new expanded tree.
            // Compute the depth of the parent of parentNode. That node is guaranteed to be a
            // parent in the current expanded tree.
            const depth = expandedParentNodeIds.findIndex(
                (id) => id === parentNode?.parentNode?.id
            );
            if (depth === -1) {
                // Drop as root or drop as the child of a root that is not part of the current
                // expanded tree. The current expanded tree should be fully closed.
                nodeToCollapse = treeExpanded?.root;
            } else {
                // Drop anywhere else (at a position that can be related to the expanded tree with
                // the depth of the parent of parentNode). In that case the existing hierarchy is
                // split at the depth of the parent, and will be completed by node's remaining
                // expanded tree.
                const nodeIdToCollapse = expandedParentNodeIds.at(depth + 1);
                if (nodeIdToCollapse) {
                    nodeToCollapse = treeExpanded?.nodePerNodeId[nodeIdToCollapse];
                }
            }
        } else {
            // Handle cases where node is a leaf dropped in the current expanded tree. In that case,
            // we only collapse the siblings of the new drop location if node was not a child of
            // that parent.
            if (oldParentNode?.id !== parentNode.id) {
                const childNodeToCollapse = parentNode.nodes.find(
                    (childNode) => !childNode.isLeaf
                );
                if (childNodeToCollapse) {
                    nodeToCollapse = childNodeToCollapse;
                }
            }
        }
        if (nodeToCollapse) {
            nodeToCollapse.collapseChildNodes(true);
        }

        // Apply changes client side.
        if (oldParentNode) {
            oldParentNode.removeChildNode(node);
        } else {
            this.root.removeTree(node.tree);
        }
        if (parentNode) {
            node.setParentNode(parentNode);
        } else {
            this.root.addNewRootNode(node);
        }
        node.data = formattedData.find((record) => record.id === resId);
        // Replace existing nodes' data with updated database values.
        for (const record of formattedData) {
            if (record.id !== resId) {
                const updatedNode = Object.values(this.root.nodePerNodeId).find(
                    (n) => n.resId === record.id
                );
                if (updatedNode) {
                    updatedNode.data = record;
                }
            }
        }
        node.hidden = false;
        this.notify({ scrollTarget: "none" });
    }
});

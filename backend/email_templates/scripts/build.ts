import { render } from '@react-email/components';
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

const TEMPLATES_DIR = path.join(__dirname, '../templates');
const OUTPUT_DIR = path.join(__dirname, '../out/emails-react');

/**
 * Extract prop names from a TypeScript interface ending with "Props" in a .tsx file.
 */
function extractPropsFromTemplate(templatePath: string): string[] {
  const sourceCode = fs.readFileSync(templatePath, 'utf-8');
  const sourceFile = ts.createSourceFile(templatePath, sourceCode, ts.ScriptTarget.Latest, true);

  const propNames: string[] = [];

  function visit(node: ts.Node) {
    if (ts.isInterfaceDeclaration(node) && node.name.text.endsWith('Props')) {
      node.members.forEach((member) => {
        if (ts.isPropertySignature(member) && ts.isIdentifier(member.name)) {
          propNames.push(member.name.text);
        }
      });
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return propNames;
}

/**
 * Build Jinja2 variable placeholders for each prop: propName -> "{{ prop_name }}"
 */
function generateJinjaProps(templatePath: string): Record<string, string> {
  const propNames = extractPropsFromTemplate(templatePath);
  const jinjaProps: Record<string, string> = {};
  for (const propName of propNames) {
    jinjaProps[propName] = `{{ ${propName} }}`;
  }
  return jinjaProps;
}

async function buildTemplate(templateName: string) {
  try {
    console.log(`Building ${templateName}...`);

    const templatePath = path.join(TEMPLATES_DIR, `${templateName}.tsx`);
    const template = await import(templatePath);
    const Component = template.default;

    if (!Component) {
      throw new Error(`No default export found in ${templateName}.tsx`);
    }

    const props = generateJinjaProps(templatePath);
    console.log(`  Props: ${Object.keys(props).join(', ') || '(none)'}`);

    // PascalCase -> snake_case: MagicLink -> magic_link
    const dirName = templateName
      .replace(/([A-Z])/g, '_$1')
      .toLowerCase()
      .replace(/^_/, '');

    const templateDir = path.join(OUTPUT_DIR, dirName);
    if (!fs.existsSync(templateDir)) {
      fs.mkdirSync(templateDir, { recursive: true });
    }

    const html = await render(Component(props), { pretty: true });
    const text = await render(Component(props), { plainText: true });

    const htmlPath = path.join(templateDir, 'html.jinja2');
    const textPath = path.join(templateDir, 'text.jinja2');

    fs.writeFileSync(htmlPath, html, 'utf-8');
    fs.writeFileSync(textPath, text, 'utf-8');

    console.log(`✓ Built ${templateName}:`);
    console.log(`  - ${htmlPath}`);
    console.log(`  - ${textPath}`);
  } catch (error) {
    console.error(`✗ Error building ${templateName}:`, error);
    throw error;
  }
}

async function buildAll() {
  console.log('Building all email templates...\n');

  if (!fs.existsSync(TEMPLATES_DIR)) {
    console.error(`Templates directory not found: ${TEMPLATES_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(TEMPLATES_DIR);
  const templateFiles = files.filter(
    (file) => file.endsWith('.tsx') && !file.startsWith('_') && file !== 'components.tsx'
  );

  if (templateFiles.length === 0) {
    console.log('No template files found.');
    return;
  }

  for (const file of templateFiles) {
    await buildTemplate(file.replace('.tsx', ''));
  }

  console.log(`\n✓ Successfully built ${templateFiles.length} template(s)`);
}

buildAll();
